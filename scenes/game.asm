; ==============================================================================
; SCENES/GAME.ASM — Main Gameplay Scene
; Target: 1 line ANTIC Mode 2 (Top Status) + 11 lines ANTIC Mode 5 (Action) + 1 line ANTIC Mode 2 (Bottom Status)
; Sprite: Animated Jabberwocky dragon (Player 0) with 16-bit Phase Accumulator
; ==============================================================================

; --- System & OS Registers ---
.ifndef ATRACT
ATRACT                  = $4D           ; OS Attract Mode timer ($4D)
.endif

; --- Dragon Configuration Constants ---
DRAGON_START_X          = 64            ; Left side of action playfield
DRAGON_START_Y          = 107           ; Centered vertically in ANTIC 5 (32..207, H=26)
DRAGON_MIN_Y            = 40            ; Top boundary (first scanline of ANTIC 5, below top status)
DRAGON_MAX_Y            = 190           ; Bottom boundary (above bottom status)
DRAGON_COLOR            = $C6           ; Dragon green (Hue $C, Lum 6)
BOTTOM_BAR_P0_X         = 48            ; Left edge of normal playfield text (column 0)
BOTTOM_BAR_M_X          = 120           ; Left edge of score last 2 digits (column 18)
DRAGON_DEATH_TARGET_X   = 48            ; Left edge of visible screen reached on death
DRAGON_DEATH_DURATION   = 100           ; ~2 seconds death sequence (100 frames @ 50Hz)
DEATH_STATE_INACTIVE    = 0             ; Normal gameplay / dragon active
DEATH_STATE_FADING      = 1             ; Fading luminance & moving to left edge
DEATH_STATE_EXPLODING   = 2             ; Explosion sound & effect
DEATH_STATE_CRASH       = 3             ; Wall collision crash sound & effect
EXPLOSION_DURATION      = 24            ; Duration of explosion in frames (~0.5s @ 50Hz)
CRASH_DURATION          = 24            ; Duration of crash sound & sequence (~0.5s @ 50Hz)

; --- Dragon Vertical Physics & Inertia (8.8 Fixed-Point) ---
DRAGON_MAX_VEL          = $0180         ; Max vertical velocity (1.5 px/frame)
DRAGON_ACCEL            = $0020         ; Acceleration per frame (smooth buildup)
DRAGON_FRICTION         = $0014         ; Deceleration / coasting drag (inertia)

; --- 16-bit Fixed-Point Animation & Momentum Constants ---
; In 8.8 fixed-point, 1 full frame step = $0100 (256 sub-steps).
; Full 6-frame cycle = 6 * 256 = 1536 ($0600) sub-steps.
; At 50 fps, 30 frames for a hover cycle -> $0600 / 30 = 51.2 = $0033 per tick.
BASE_HOVER_SPEED        = $0033         ; Base hover rate (~5 video frames per animation frame)
MOMENTUM_DIVISOR        = 4             ; Division by 4 for scroll momentum (via 2x LSR)
SCROLL_MAX_SPEED        = $0300         ; Max horizontal scroll velocity (3.0 px/frame)
SCROLL_BASE_SPEED       = $00C0         ; Base forward cruising speed (~0.75 px/frame)
SCROLL_MIN_SPEED        = $0030         ; Minimum crawl speed when braking
SCROLL_ACCEL            = $0010         ; Scroll acceleration rate when holding Right
SCROLL_BRAKE            = $0024         ; Scroll braking rate when holding Left
SCROLL_DRAG             = $0006         ; Momentum decay towards hover when neutral
SCROLL_COL_THRESHOLD    = $0400         ; 4 color clocks (8 pixels) = 1 Mode 5 column

game_init
    ; Blank DMA during reconfiguration
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset PMG
    jsr disable_pmg

    ; Clear Player 0, 1, 2, 3 buffers ($2400-$27FF) and Missiles ($2300-$23FF)
    ldx #0
    lda #0
@   sta P0_ADDR,x
    sta P1_ADDR,x
    sta P2_ADDR,x
    sta P3_ADDR,x
    sta M_ADDR,x
    inx
    bne @-

    ; Fill 8 lines of Player 0, 1, 2, 3 and Missiles with $FF for bottom status bar overlay
    ldx bot_bar_pmg_y
    ldy #7
    lda #$FF
@fill_p_bot
    sta P0_ADDR,x
    sta P1_ADDR,x
    sta P2_ADDR,x
    sta P3_ADDR,x
    sta M_ADDR,x
    inx
    dey
    bpl @fill_p_bot

    ; Set PMBASE (page $20 = $2000)
    lda #>PM_ADDR
    sta PMBASE

    ; Configure Player 0 hardware
    lda #DRAGON_START_X
    sta HPOSP0
    lda #0
    sta SIZEP0              ; Normal width (8 color clocks)
    lda pal_action_dragon
    sta PCOLR0
    sta COLPM0

    ; Priority: Player 0 in front of playfield + 5th player mode for missiles ($09)
    lda #$09
    sta GPRIOR
    sta PRIOR

    ; Enable player and missile display in GTIA (bit 0=missiles, bit 1=players)
    lda #3
    sta GRACTL
    sta HITCLR

    ; Reset missile hardware registers and fire state
    lda #0
    sta HPOSM0
    sta HPOSM1
    sta HPOSM2
    sta HPOSM3
    sta SIZEM
    sta AUDCTL
    sta AUDC1
    sta AUDC2
    sta AUDC3
    sta AUDC4
    sta fire_state
    sta fire_frame
    sta fire_timer
    sta fire_prev_y

    ; Initialize Dragon vertical physics variables
    lda #DRAGON_START_Y
    sta dragon_y
    sta dragon_prev_y
    lda #0
    sta dragon_sub_y
    sta dragon_vel_lo
    sta dragon_vel_hi

    ; Initialize 16-bit Animation & Scroll variables
    sta ANIM_PHASE
    sta ANIM_PHASE+1
    lda #<SCROLL_BASE_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_BASE_SPEED
    sta SCROLL_SPEED+1
    lda #3
    sta hscrol_fine
    sta HSCROL

    ; Calculate initial ANIM_SPEED = BASE_HOVER_SPEED + (0 / 4)
    jsr update_anim_speed

    ; Use default text font ($7000)
    lda #>FONT_ADDR
    sta CHBASE
    sta CHBAS

    ; Set DLIST pointer to main game display list
    lda #<dlist_game
    sta SDLSTL
    sta DLISTL
    lda #>dlist_game
    sta SDLSTH
    sta DLISTH

    ; Initialize action screen colors from compiled world/colors.yaml
    lda world_color_pf0
    sta pal_action_pf0
    sta COLOR0
    sta COLPF0
    lda world_color_pf1
    sta pal_action_pf1
    sta COLOR1
    sta COLPF1
    lda world_color_pf2
    sta pal_action_pf2
    sta COLOR2
    sta COLPF2
    lda world_color_pf3
    sta pal_action_breath
    sta COLOR3
    sta COLPF3
    lda world_color_bk
    sta pal_action_bk
    sta COLOR4
    sta COLBK

    ; Set fallback player/missile colors
    lda pal_action_p1
    sta PCOLR1
    sta COLPM1
    lda pal_action_p2
    sta PCOLR2
    sta COLPM2
    lda pal_action_p3
    sta PCOLR3
    sta COLPM3

    ; Initialize world level & screens streaming (starts with level 0)
    lda #0
    sta current_level_idx
    jsr init_level_screens

    ; Clear status bar row 0 ($6200-$6227) with 0 (normal space)
    lda #0
    ldx #39
@   sta GAME_STATUS_VRAM,x
    dex
    bpl @-

    ; Clear status bar row 1 ($6228-$624F) with $80 (inverse space)
    lda #$80
    ldx #39
@   sta GAME_STATUS_VRAM+40,x
    dex
    bpl @-

    ; Enable inverse video in CHACTL
    lda #2
    sta CHACTL

    ; Initialize dragon energy bar (row 0) and counters
    jsr init_energy_bar
    lda #0
    sta GAME_OVER_REASON
    sta dragon_dying
    sta dragon_recharging
    sta dragon_p0pf
    sta flame_m_pf
    sta death_timer
    sta death_move_timer
    sta HITCLR

    lda #DRAGON_START_X
    sta dragon_x
    lda #DRAGON_START_Y
    sta dragon_y
    lda #DRAGON_COLOR
    sta pal_action_dragon

    ; Compute initial dragon energy frames (~30 seconds) based on PAL/NTSC
    jsr calc_energy_frames
    ; Initialize game status values (LEVEL, LIVES, SCORE, SHOTS)
    lda #1
    sta LEVEL
    sta SHOTS                   ; Initial dragon fire shots = 1
    lda #3
    sta LIVES
    lda #LIVES_BLINK_PERIOD
    sta lives_blink_timer
    lda #0
    sta lives_blink_state
    lda #0
    ldx #3                      ; Score is now 4 digits (0..3)
@init_score
    sta SCORE,x
    dex
    bpl @init_score

    ; Draw initial bottom status bar (row 1)
    jsr draw_bottom_status

    ; Initialize charset animations state
    jsr init_charset_animation

    ; Initialize flame collision state
    jsr init_flame_collision

    ; Initial render of dragon sprite into Player 0 buffer
    jsr render_dragon

    ; Set initial DLI vector (points to top status bar handler)
    lda #<dli_game_top
    sta VDSLST
    lda #>dli_game_top
    sta VDSLST+1

    ; Install Deferred VBLANK vector via OS SETVBV
    ldy #<vblank_game
    ldx #>vblank_game
    lda #7                      ; Type 7 = Deferred VBLANK
    jsr SETVBV

    ; Enable playfield DMA + single-line PMG + Player DMA + Missile DMA (%00111110 = $3E)
    lda #$3E
    sta SDMCTL
    sta DMACTL

    ; Enable NMI: VBLANK ($40) + DLI ($80) = $C0
    lda #$C0
    sta NMIEN
    rts

game_run
    ; 1. Check if game over already triggered
    lda GAME_OVER_REASON
    bne @exit_to_game_over

    ; 2. Check START console key to exit to Game Over
    lda CONSOL
    and #$01
    bne @not_start

    lda #REASON_PLAYER_QUIT
    sta GAME_OVER_REASON

@exit_to_game_over
    ; Disable DLI before leaving scene
    lda #$40                    ; VBLANK only, DLI disabled
    sta NMIEN

    ; Restore default deferred VBLANK vector
    ldy #<XITVBV
    ldx #>XITVBV
    lda #7                      ; Deferred VBLANK
    jsr SETVBV

    jsr disable_pmg
    lda #STATE_GAME_OVER
    sta game_state
    rts

@not_start
    ; Reset OS Attract Mode timer to prevent color shifting during gameplay
    lda #0
    sta ATRACT

    ; 3. Check if dragon is in death sequence
    lda dragon_dying
    beq @dragon_controls_active

    ; Dragon is dying: update death sequence (controls disabled)
    jsr update_dragon_death
    lda GAME_OVER_REASON
    bne @exit_to_game_over
    jmp @render_frame

@dragon_controls_active
    ; 4. Check FIRE button to trigger fire breathing
    lda fire_pressed
    beq @not_fire
    lda #0
    sta fire_pressed
    lda fire_state
    bne @not_fire           ; If already firing, ignore subsequent press
    lda SHOTS
    beq @not_fire           ; If no shots remaining, cannot fire!
    dec SHOTS
    jsr update_bottom_status ; Update shots display immediately
    jsr start_fire

@not_fire

    ; 2. Read Joystick 0 (STICK0) — Vertical movement with acceleration & inertia
    ; Bit 0 = 0: UP pushed -> Accelerate UP (subtract ACCEL from velocity)
    lda STICK0
    and #$01
    bne @check_down

    ; Accelerate UP: vel -= DRAGON_ACCEL
    lda dragon_vel_lo
    sec
    sbc #<DRAGON_ACCEL
    sta dragon_vel_lo
    lda dragon_vel_hi
    sbc #>DRAGON_ACCEL
    sta dragon_vel_hi

    ; Clamp to -DRAGON_MAX_VEL ($FE80 = -$0180)
    lda dragon_vel_hi
    bpl @up_clamp_ok
    cmp #>$FE80
    bne @chk_hi_up
    lda dragon_vel_lo
    cmp #<$FE80
@chk_hi_up
    bcs @up_clamp_ok
    lda #<$FE80
    sta dragon_vel_lo
    lda #>$FE80
    sta dragon_vel_hi
@up_clamp_ok
    jmp @vert_physics_done

@check_down
    ; Bit 1 = 0: DOWN pushed -> Accelerate DOWN (add ACCEL to velocity)
    lda STICK0
    and #$02
    bne @apply_friction

    ; Accelerate DOWN: vel += DRAGON_ACCEL
    lda dragon_vel_lo
    clc
    adc #<DRAGON_ACCEL
    sta dragon_vel_lo
    lda dragon_vel_hi
    adc #>DRAGON_ACCEL
    sta dragon_vel_hi

    ; Clamp to +DRAGON_MAX_VEL ($0180)
    lda dragon_vel_hi
    bmi @dn_clamp_ok
    cmp #>$0180
    bne @chk_hi_dn
    lda dragon_vel_lo
    cmp #<$0180
@chk_hi_dn
    bcc @dn_clamp_ok
    lda #<$0180
    sta dragon_vel_lo
    lda #>$0180
    sta dragon_vel_hi
@dn_clamp_ok
    jmp @vert_physics_done

@apply_friction
    ; Neither UP nor DOWN pushed -> Coasting / Inertia (apply friction towards 0)
    lda dragon_vel_hi
    bne @coast_active
    lda dragon_vel_lo
    beq @vert_physics_done

@coast_active
    lda dragon_vel_hi
    bmi @coast_upward

    ; Moving downward (positive velocity) -> subtract friction
    lda dragon_vel_lo
    sec
    sbc #<DRAGON_FRICTION
    sta dragon_vel_lo
    lda dragon_vel_hi
    sbc #>DRAGON_FRICTION
    sta dragon_vel_hi
    bpl @vert_physics_done
    lda #0
    sta dragon_vel_lo
    sta dragon_vel_hi
    jmp @vert_physics_done

@coast_upward
    ; Moving upward (negative velocity) -> add friction
    lda dragon_vel_lo
    clc
    adc #<DRAGON_FRICTION
    sta dragon_vel_lo
    lda dragon_vel_hi
    adc #>DRAGON_FRICTION
    sta dragon_vel_hi
    bmi @vert_physics_done
    lda #0
    sta dragon_vel_lo
    sta dragon_vel_hi

@vert_physics_done
    ; Apply 16-bit velocity to 8.8 vertical position
    lda dragon_sub_y
    clc
    adc dragon_vel_lo
    sta dragon_sub_y
    lda dragon_y
    adc dragon_vel_hi
    sta dragon_y

    ; Boundary check and clamping:
    lda dragon_y
    cmp #DRAGON_MIN_Y
    bcs @chk_bottom
    lda #DRAGON_MIN_Y
    sta dragon_y
    lda #0
    sta dragon_sub_y
    sta dragon_vel_lo
    sta dragon_vel_hi
    jmp @check_scroll

@chk_bottom
    cmp #DRAGON_MAX_Y
    bcc @check_scroll
    beq @check_scroll
    lda #DRAGON_MAX_Y
    sta dragon_y
    lda #0
    sta dragon_sub_y
    sta dragon_vel_lo
    sta dragon_vel_hi

@check_scroll
    ; 3. Read Joystick 0 (STICK0) — Horizontal momentum & scroll speed control
    ; Bit 3 = 0: RIGHT pushed -> Accelerate forward (increase SCROLL_SPEED)
    lda STICK0
    and #$08
    bne @check_scroll_left

    ; Accelerate scroll speed: SCROLL_SPEED += SCROLL_ACCEL
    lda SCROLL_SPEED
    clc
    adc #<SCROLL_ACCEL
    sta SCROLL_SPEED
    lda SCROLL_SPEED+1
    adc #>SCROLL_ACCEL
    sta SCROLL_SPEED+1

    ; Clamp to SCROLL_MAX_SPEED ($0300 = 3.0 px/frame)
    cmp #>SCROLL_MAX_SPEED
    bne @chk_scr_hi
    lda SCROLL_SPEED
    cmp #<SCROLL_MAX_SPEED
@chk_scr_hi
    bcc @scroll_right_ok
    lda #<SCROLL_MAX_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_MAX_SPEED
    sta SCROLL_SPEED+1
@scroll_right_ok
    jmp @scroll_updated

@check_scroll_left
    ; Bit 2 = 0: LEFT pushed -> Brake / decelerate (decrease SCROLL_SPEED)
    lda STICK0
    and #$04
    bne @scroll_neutral

    ; Brake scroll speed: SCROLL_SPEED -= SCROLL_BRAKE
    lda SCROLL_SPEED
    sec
    sbc #<SCROLL_BRAKE
    sta SCROLL_SPEED
    lda SCROLL_SPEED+1
    sbc #>SCROLL_BRAKE
    sta SCROLL_SPEED+1

    ; Clamp to minimum speed SCROLL_MIN_SPEED
    lda SCROLL_SPEED+1
    bmi @clamp_min_speed
    bne @scroll_updated
    lda SCROLL_SPEED
    cmp #<SCROLL_MIN_SPEED
    bcs @scroll_updated
@clamp_min_speed
    lda #<SCROLL_MIN_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_MIN_SPEED
    sta SCROLL_SPEED+1
    jmp @scroll_updated

@scroll_neutral
    ; Neither Left nor Right held -> Coasting / momentum decay towards SCROLL_BASE_SPEED
    lda SCROLL_SPEED+1
    cmp #>SCROLL_BASE_SPEED
    bne @cmp_neutral_hi
    lda SCROLL_SPEED
    cmp #<SCROLL_BASE_SPEED
@cmp_neutral_hi
    beq @scroll_updated             ; Exactly at base speed
    bcs @drag_down                  ; Faster than base speed -> decelerate

    ; Slower than base speed -> gently accelerate towards base speed
    lda SCROLL_SPEED
    clc
    adc #<SCROLL_DRAG
    sta SCROLL_SPEED
    lda SCROLL_SPEED+1
    adc #>SCROLL_DRAG
    sta SCROLL_SPEED+1
    ; Don't overshoot
    lda SCROLL_SPEED+1
    cmp #>SCROLL_BASE_SPEED
    bne @chk_neutral_acc_hi
    lda SCROLL_SPEED
    cmp #<SCROLL_BASE_SPEED
@chk_neutral_acc_hi
    bcc @scroll_updated
    lda #<SCROLL_BASE_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_BASE_SPEED
    sta SCROLL_SPEED+1
    jmp @scroll_updated

@drag_down
    lda SCROLL_SPEED
    sec
    sbc #<SCROLL_DRAG
    sta SCROLL_SPEED
    lda SCROLL_SPEED+1
    sbc #>SCROLL_DRAG
    sta SCROLL_SPEED+1
    ; Don't undershoot
    lda SCROLL_SPEED+1
    cmp #>SCROLL_BASE_SPEED
    bne @chk_neutral_drag_hi
    lda SCROLL_SPEED
    cmp #<SCROLL_BASE_SPEED
@chk_neutral_drag_hi
    bcs @scroll_updated
    lda #<SCROLL_BASE_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_BASE_SPEED
    sta SCROLL_SPEED+1

@scroll_updated
    ; 4. Recalculate dynamic ANIM_SPEED = BASE_HOVER_SPEED + (SCROLL_SPEED / 4)
    jsr update_anim_speed

    ; Update world playfield scrolling & level streaming
    jsr update_world_scrolling

    ; Update fire breathing animation & sound
    jsr update_fire
    jsr update_fire_sound

@render_frame
    ; Update bottom status bar display (handles blinking when LIVES == 1)
    jsr update_bottom_status

    ; 5. Commit/render sprite to Player 0 buffer & missiles to M_ADDR
    jsr render_dragon
    jsr render_fire
    rts

; ==============================================================================
; DYNAMIC ANIMATION SPEED CALCULATION
; Formula: ANIM_SPEED = BASE_HOVER_SPEED + (SCROLL_SPEED / MOMENTUM_DIVISOR)
; MOMENTUM_DIVISOR = 4 (implemented via 2-bit right shift)
; ==============================================================================
update_anim_speed
    ; 16-bit right shift by 2: (SCROLL_SPEED / 4)
    lda SCROLL_SPEED+1              ; Load high byte of scroll speed
    lsr                             ; Shift right, carry = bit 0
    sta ZP_TMP                      ; Store intermediate shifted high byte
    lda SCROLL_SPEED                ; Load low byte of scroll speed
    ror                             ; Rotate right with carry from high byte
    lsr ZP_TMP                      ; Shift right second time (divisor = 4)
    ror                             ; Rotate right second time
    ; A holds low byte of (SCROLL_SPEED / 4)
    ; ZP_TMP holds high byte of (SCROLL_SPEED / 4)

    ; Add BASE_HOVER_SPEED (16-bit ADC)
    clc                             ; Clear carry before addition
    adc #<BASE_HOVER_SPEED          ; Add base hover low byte ($33)
    sta ANIM_SPEED                  ; Store in ANIM_SPEED Low Byte
    lda ZP_TMP
    adc #>BASE_HOVER_SPEED          ; Add base hover high byte ($00) + carry
    sta ANIM_SPEED+1                ; Store in ANIM_SPEED High Byte
    rts

; ==============================================================================
; VBLANK ANIMATION STEP — 16-bit Phase Accumulator (Optimized 8-Frame Bitmask)
; Performs ANIM_PHASE = ANIM_PHASE + ANIM_SPEED via 16-bit ADC
; Applies bitwise mask AND #%00000111 (AND #7) on High Byte to wrap across 8 frames
; Stores masked High Byte back to memory and returns X as safe index (0..7)
; ==============================================================================
vblank_anim_step
    clc                             ; Clear carry before 16-bit addition
    lda ANIM_PHASE                  ; Low Byte of accumulator (fractional phase)
    adc ANIM_SPEED                  ; Add Low Byte of step rate
    sta ANIM_PHASE                  ; Store updated fractional phase

    lda ANIM_PHASE+1                ; High Byte of accumulator (frame index)
    adc ANIM_SPEED+1                ; Add High Byte of step rate + carry

    ; Power-of-two frame wrap (8 frames: indices 0 to 7) via single bitwise mask
    and #%00000111                  ; Mask High Byte to 0..7 (replaces CMP/SBC check)
    sta ANIM_PHASE+1                ; Store masked frame index back to memory

    tax                             ; X = safe animation frame index (0..7)
    rts

; ==============================================================================
; RENDER DRAGON — Clears previous 26 sprite lines and copies current frame to P0
; Synchronized with VBLANK at top of frame to prevent visual tearing
; Uses frame pointer lookup tables to rapidly fetch 26-byte frame starting addresses
; ==============================================================================
render_dragon
    ; Clear previous 26 lines in Player 0 RAM
    ldx dragon_prev_y
    lda #0
    ldy #26                         ; Exactly 26 scanlines to clear
@   sta P0_ADDR,x
    inx
    dey
    bne @-

    ; If dragon is exploding or crashing, skip drawing new sprite (dragon is vaporized/destroyed)
    lda dragon_dying
    cmp #DEATH_STATE_EXPLODING
    beq @keep_p_bot_overlay
    cmp #DEATH_STATE_CRASH
    beq @keep_p_bot_overlay

    ; Advance 16-bit Phase Accumulator (returns X = safe frame index 0..7)
    jsr vblank_anim_step

    ; Rapidly fetch frame starting address via Low/High pointer lookup tables
    lda dragon_frame_tbl_lo,x
    sta PTR_SRC
    lda dragon_frame_tbl_hi,x
    sta PTR_SRC+1

    ; Copy 26 bytes of current frame into P0_ADDR + dragon_y
    ldx dragon_y
    stx dragon_prev_y               ; Update prev_y for next frame's erasure
    ldy #0
@   lda (PTR_SRC),y
    sta P0_ADDR,x
    inx
    iny
    cpy #26                         ; Exactly 26 bytes copied
    bne @-

@keep_p_bot_overlay
    ; Ensure bottom status bar overlay stays $FF for Players 0, 1, 2, 3 and Missiles
    ldx bot_bar_pmg_y
    ldy #7
    lda #$FF
@keep_p_bot
    sta P0_ADDR,x
    sta P1_ADDR,x
    sta P2_ADDR,x
    sta P3_ADDR,x
    sta M_ADDR,x
    inx
    dey
    bpl @keep_p_bot
    rts

; ==============================================================================
; BOTTOM STATUS BAR SYSTEM
; Displays LEVEL, SCORE (4 digits), LIVES, and SHOTS on status bar row 1
; Layout: "LEVEL:01  SCORE:0000  LIVES:03  SHOTS:01" (40 chars)
; ==============================================================================
draw_bottom_status
    lda #<status_bottom_txt
    sta PTR_SRC
    lda #>status_bottom_txt
    sta PTR_SRC+1
    ldx #1
    jsr print_status_line
    ; Fall through to update_bottom_status

update_bottom_status
    ; Update LEVEL 2 digits (columns 6..7 -> GAME_STATUS_VRAM + 46..47)
    lda LEVEL
    jsr format_2digits
    stx GAME_STATUS_VRAM + 46   ; Tens
    sta GAME_STATUS_VRAM + 47   ; Units

    ; Update SCORE 4 digits (columns 16..19 -> GAME_STATUS_VRAM + 56..59)
    ldx #0
@score_loop
    lda SCORE,x
    clc
    adc #$90
    sta GAME_STATUS_VRAM + 56,x
    inx
    cpx #4
    bne @score_loop

    ; Update LIVES 2 digits (columns 28..29 -> GAME_STATUS_VRAM + 68..69)
    lda LIVES
    jsr format_2digits
    stx GAME_STATUS_VRAM + 68   ; Tens
    sta GAME_STATUS_VRAM + 69   ; Units

    ; Check if LIVES == 1 for blinking
    lda LIVES
    cmp #1
    bne @lives_steady

    ; LIVES == 1: Blink digit every half second (25 frames @ 50Hz)
    dec lives_blink_timer
    bne @lives_draw_blink
    lda #LIVES_BLINK_PERIOD
    sta lives_blink_timer
    lda lives_blink_state
    eor #1
    sta lives_blink_state

@lives_draw_blink
    lda lives_blink_state
    bne @lives_blank

    ; State 0: visible '1' ($91)
    lda #$91
    sta GAME_STATUS_VRAM + 69
    jmp @update_shots

@lives_blank
    ; State 1: hidden / inverse blank space ($80)
    lda #$80
    sta GAME_STATUS_VRAM + 69
    jmp @update_shots

@lives_steady
    ; LIVES != 1: always steady, reset blink state & timer
    lda #LIVES_BLINK_PERIOD
    sta lives_blink_timer
    lda #0
    sta lives_blink_state

@update_shots
    ; Update SHOTS 2 digits (columns 38..39 -> GAME_STATUS_VRAM + 78..79)
    lda SHOTS
    jsr format_2digits
    stx GAME_STATUS_VRAM + 78   ; Tens
    sta GAME_STATUS_VRAM + 79   ; Units
    rts

; Helper subroutine: converts A (0..99) to inverted ANTIC display codes
; Returns: X = tens digit ($90..$99), A = units digit ($90..$99)
format_2digits
    ldx #0
@div10_loop
    cmp #10
    bcc @div10_done
    sec
    sbc #10
    inx
    bne @div10_loop
@div10_done
    tay                 ; Y = units (0..9)
    txa                 ; A = tens (0..9)
    clc
    adc #$90
    tax                 ; X = inverted tens character code
    tya                 ; A = units (0..9)
    clc
    adc #$90            ; A = inverted units character code
    rts

; Print text string to status bar row (X = 0 or 1)
; String format: [1 byte length, followed by internal display codes]
print_status_line
    lda status_line_lo,x
    sta PTR_DST
    lda #>GAME_STATUS_VRAM
    sta PTR_DST+1

    ldy #0
    lda (PTR_SRC),y
    beq @print_done
    tax                 ; X = length counter

    ldy #1
@   lda (PTR_SRC),y
    ora #$80            ; Inverted video text (bit 7 = 1)
    dey
    sta (PTR_DST),y     ; Store inverted character in VRAM
    iny
    iny
    dex
    bne @-

@print_done
    rts

; ==============================================================================
; FIRE BREATHING SYSTEM (4 PMG Missiles M0..M3)
; ==============================================================================

start_fire
    lda #1
    sta fire_state          ; State: 1 = EXPANDING
    lda #0
    sta fire_frame          ; Start at Frame 0
    tax
    lda fire_duration_tbl,x ; Initial frame duration (7 frames)
    sta fire_timer
    rts

update_fire
    lda fire_state
    bne @uf_active
    rts

@uf_active
    dec fire_timer
    bne @uf_done

    ; Timer expired, advance state machine
    lda fire_state
    cmp #1                  ; Expanding?
    beq @advance_expand
    cmp #2                  ; Peak hold?
    beq @advance_peak
    ; Otherwise: Retracting (3)
    jmp @advance_retract

@advance_expand
    inc fire_frame
    lda fire_frame
    cmp #7
    bne @set_expand_timer
    ; Reached frame 7 (Peak!)
    lda #2
    sta fire_state          ; State: 2 = PEAK HOLD
    lda #2
    sta fire_timer          ; Hold peak for 2 frames
    rts

@set_expand_timer
    ldx fire_frame
    lda fire_duration_tbl,x
    sta fire_timer
    rts

@advance_peak
    ; Peak hold finished, start retracting
    lda #3
    sta fire_state          ; State: 3 = RETRACTING
    lda #6
    sta fire_frame
    ldx #6
    lda fire_duration_tbl,x ; 1 frame
    sta fire_timer
    rts

@advance_retract
    lda fire_frame
    beq @retract_done       ; Frame 0 finished -> extinguish
    dec fire_frame
    ldx fire_frame
    lda fire_duration_tbl,x
    sta fire_timer
    rts

@retract_done
    lda #0
    sta fire_state
    rts

@uf_done
    rts

; Render fire: updates M_ADDR and GTIA registers (HPOSM0..3, SIZEM)
render_fire
    ; If fire was previously rendered, clear previous 7 lines in M_ADDR
    lda fire_prev_y
    beq @check_active
    tax
    lda #0
    ldy #7
@   sta M_ADDR,x
    inx
    dey
    bne @-
    lda #0
    sta fire_prev_y

@check_active
    lda fire_state
    bne @render_active
    ; Inactive: clear HPOSM0..3 and SIZEM
    lda #0
    sta cur_hposm0
    sta cur_hposm1
    sta cur_hposm2
    sta cur_hposm3
    sta cur_sizem
    sta HPOSM0
    sta HPOSM1
    sta HPOSM2
    sta HPOSM3
    sta SIZEM
    rts

@render_active
    ; Compute destination Y = dragon_y + 10
    lda dragon_y
    clc
    adc #10
    sta fire_prev_y
    tax

    ; Fetch flame pattern start index
    ldy fire_frame
    lda fire_pattern_idx,y
    tay

    ; Copy 7 scanlines into M_ADDR
    lda fire_pattern_data,y
    sta M_ADDR,x
    inx
    iny
    lda fire_pattern_data,y
    sta M_ADDR,x
    inx
    iny
    lda fire_pattern_data,y
    sta M_ADDR,x
    inx
    iny
    lda fire_pattern_data,y
    sta M_ADDR,x
    inx
    iny
    lda fire_pattern_data,y
    sta M_ADDR,x
    inx
    iny
    lda fire_pattern_data,y
    sta M_ADDR,x
    inx
    iny
    lda fire_pattern_data,y
    sta M_ADDR,x

    ; Set SIZEM from table
    ldx fire_frame
    lda fire_sizem_tbl,x
    sta cur_sizem
    sta SIZEM

    ; Compute and set HPOSM0..3 = dragon_x + offset (or 0 if inactive)
    lda fire_off_m0,x
    beq @m0_off
    clc
    adc dragon_x
@m0_off
    sta cur_hposm0
    sta HPOSM0

    lda fire_off_m1,x
    beq @m1_off
    clc
    adc dragon_x
@m1_off
    sta cur_hposm1
    sta HPOSM1

    lda fire_off_m2,x
    beq @m2_off
    clc
    adc dragon_x
@m2_off
    sta cur_hposm2
    sta HPOSM2

    lda fire_off_m3,x
    beq @m3_off
    clc
    adc dragon_x
@m3_off
    sta cur_hposm3
    sta HPOSM3
    rts

; ==============================================================================
; FIRE BREATHING SOUND SYSTEM (POKEY Channels 1 & 2)
; Channel 1: Low-frequency roaring rumble (5-bit + 17-bit noise, distortion $0x)
; Channel 2: Rushing flame burst / wind hiss (17-bit noise, distortion $8x)
; Dynamic volume and frequency tracking fire_frame with micro-jitter turbulence
; ==============================================================================
update_fire_sound
    lda fire_state
    bne @snd_active

    ; Silence both fire sound channels when fire is inactive
    lda #0
    sta AUDC1
    sta AUDC2
    rts

@snd_active
    ldx fire_frame                  ; Current animation frame (0..7)

    ; --- Channel 1: Deep Roaring Rumble ---
    lda RTCLOK+2
    and #$03                        ; 0..3 micro-jitter for organic turbulence
    clc
    adc fire_snd_audf1,x
    sta AUDF1
    lda fire_snd_audc1,x            ; Volume (0..15) with distortion $00
    sta AUDC1

    ; --- Channel 2: Rushing Flame Hiss ---
    lda RTCLOK+2
    eor #$05
    and #$03                        ; Independent micro-jitter
    clc
    adc fire_snd_audf2,x
    sta AUDF2
    lda fire_snd_audc2,x            ; Volume (0..15) with distortion $80
    sta AUDC2
    rts

; ==============================================================================
; DLI ROUTINES FOR GAMEPLAY SCREEN
; DLI 1: Before top status bar -> Set 8-scanline color bar gradient for text/bar
; DLI 2: After top status bar -> Restore action playfield palette (colors 0..4)
; DLI 3: Before bottom status bar -> Set 8-scanline color bar gradient for bottom status
; ==============================================================================

dli_game_top
    pha                         ; [3] (3) Save accumulator
    txa                         ; [2] (5)
    pha                         ; [3] (8) Save X register

    lda #0                      ; Reset HSCROL for top status bar
    sta HSCROL

    lda #>FONT_ADDR             ; [2] (10) Text font for status bar
    sta CHBASE                  ; [4] (14)
    lda pal_top_bk              ; [4] (18) Top status background: blue
    sta COLPF2                  ; [4] (22) In Mode 2 (normal text): COLPF2 = background
    lda #<dli_game_action       ; [2] (24) Chain to DLI 2 (restore action palette)
    sta VDSLST                  ; [4] (28)
    lda #>dli_game_action       ; [2] (30)
    sta VDSLST+1                ; [4] (34)

    ldx #0                      ; [2] (36) Initialize scanline index (0..7)
@top_bar_loop
    lda pal_top_bar,x           ; [4] (40) Load color value for current scanline
    sta WSYNC                   ; [4] (44) Wait for horizontal sync
    sta COLPF1                  ; [4] (4)  Set character luminance at start of scanline
    inx                         ; [2] (6)
    cpx #8                      ; [2] (8)
    bne @top_bar_loop           ; [3/2] (11/10) Loop across 8 scanlines of Mode 2

    pla                         ; [4] (14)
    tax                         ; [2] (16) Restore X register
    pla                         ; [4] (20) Restore accumulator
    rti                         ; [6] (26) Return from interrupt

dli_game_action
    pha                         ; [3] (3) Save accumulator
    sta WSYNC                   ; [4] (7) Wait for horizontal sync

    lda #>GAME_FONT_ADDR        ; [2] (9) Action playfield character set
    sta CHBASE                  ; [4] (13)

    lda hscrol_fine             ; Fine horizontal scroll for action playfield
    sta HSCROL

    ; Restore Player 0 hardware registers for dragon & disable P1/P2/P3 in action area
    lda dragon_x                ; [4] (17) Player 0 position
    sta HPOSP0                  ; [4] (21)
    lda #0                      ; [2] (23) Normal width (1x) & offscreen for unused sprites
    sta SIZEP0                  ; [4] (27)
    sta SIZEP1                  ; [4] (31)
    sta SIZEP2                  ; [4] (35)
    sta SIZEP3
    sta HPOSP1                  ; [4] (39) Inactive in action area
    sta HPOSP2                  ; [4] (43) Inactive in action area
    sta HPOSP3

    ; Restore missiles from active fire state
    lda cur_sizem
    sta SIZEM
    lda cur_hposm0
    sta HPOSM0
    lda cur_hposm1
    sta HPOSM1
    lda cur_hposm2
    sta HPOSM2
    lda cur_hposm3
    sta HPOSM3

    ; Restore entire action playfield palette from memory cells
    lda pal_action_dragon       ; [4] (47) Player 0: Dragon body
    sta COLPM0                  ; [4] (51)
    lda pal_action_breath       ; [4] (55) Missiles (5th player): Dragon breath / flame
    sta COLPF3                  ; [4] (59)
    lda pal_action_pf0          ; [4] (63) Playfield color 0
    sta COLPF0                  ; [4] (67)
    lda pal_action_pf1          ; [4] (71) Playfield color 1
    sta COLPF1                  ; [4] (75)
    lda pal_action_pf2          ; [4] (79) Playfield color 2
    sta COLPF2                  ; [4] (83)
    lda pal_action_bk           ; [4] (87) Background color & border
    sta COLBK                   ; [4] (91)

    sta HITCLR                  ; [4] (95) Clear collision latches right before action area starts

    lda #<dli_game_bottom       ; [2] (97) Chain to DLI 3 (bottom status)
    sta VDSLST                  ; [4] (101)
    lda #>dli_game_bottom       ; [2] (103)
    sta VDSLST+1                ; [4] (107)
    pla                         ; [4] (111) Restore accumulator
    rti                         ; [6] (117) Return from interrupt

dli_game_bottom
    pha                         ; [3] (3) Save accumulator
    txa                         ; [2] (5)
    pha                         ; [3] (8) Save X register

    lda P0PF                    ; Capture dragon collisions from action area
    sta dragon_p0pf
    lda M0PF                    ; Capture missile flame collisions from action area
    ora M1PF
    ora M2PF
    ora M3PF
    sta flame_m_pf
    sta HITCLR                  ; Clear collision latches before bottom status bar begins

    lda #0                      ; Reset HSCROL for bottom status bar
    sta HSCROL

    lda #>FONT_ADDR             ; [2] (10) Restore text font for bottom status
    sta CHBASE                  ; [4] (14)
    lda pal_bottom_bk           ; [4] (18) Bottom status background: black/purple
    sta COLPF2                  ; [4] (22) In Mode 2 (normal text): COLPF2 = background
    lda #<dli_game_top          ; [2] (24) Reset DLI vector to top handler for next frame
    sta VDSLST                  ; [4] (28)
    lda #>dli_game_top          ; [2] (30)
    sta VDSLST+1                ; [4] (34)

    ; Reconfigure Players 0, 1, 2, 3 for bottom status overlay (x4 width)
    lda bot_bar_p0_x            ; [4] (30) "LEVEL:01"
    sta HPOSP0                  ; [4] (34)
    lda bot_bar_p1_x            ; [4] (38) "SCORE:"
    sta HPOSP1                  ; [4] (42)
    lda bot_bar_p2_x            ; [4] (46) "LIVES:03"
    sta HPOSP2                  ; [4] (50)
    lda bot_bar_p3_x            ; [4] (54) "SHOTS:01"
    sta HPOSP3                  ; [4] (58)

    lda #3                      ; [2] (60) Quadruple width (x4)
    sta SIZEP0                  ; [4] (64)
    sta SIZEP1                  ; [4] (68)
    sta SIZEP2                  ; [4] (72)
    sta SIZEP3                  ; [4] (76)

    lda pal_bottom_p0           ; [4] (80) Color P0 (cyan)
    sta COLPM0                  ; [4] (84)
    lda pal_bottom_p1           ; [4] (88) Color P1 (blue-cyan)
    sta COLPM1                  ; [4] (92)
    lda pal_bottom_p2           ; [4] (96) Color P2 (yellow)
    sta COLPM2                  ; [4] (100)
    lda pal_bottom_p3           ; [4] (104) Color P3 (orange/red)
    sta COLPM3                  ; [4] (108)

    ; Configure Missile 1 to cover last 2 digits of SCORE (cols 18..19, X=120)
    lda bot_bar_m_x             ; [4] X = 120
    sta HPOSM1                  ; [4]
    lda #0                      ; [2]
    sta HPOSM0                  ; [4]
    sta HPOSM2                  ; [4]
    sta HPOSM3                  ; [4]
    lda #$0C                    ; [2] M1 quadruple width (%00001100)
    sta SIZEM                   ; [4]
    lda pal_bottom_m            ; [4] Color M1 (blue-cyan, matching SCORE)
    sta COLPF3                  ; [4]

    ldx #0                      ; [2] (48) Initialize scanline index (0..7)
@bot_bar_loop
    lda pal_bottom_bar,x        ; [4] (52) Load color value for current scanline
    sta WSYNC                   ; [4] (56) Wait for horizontal sync
    sta COLPF1                  ; [4] (4)  Set character luminance at start of scanline
    inx                         ; [2] (6)
    cpx #8                      ; [2] (8)
    bne @bot_bar_loop           ; [3/2] (11/10) Loop across 8 scanlines of Mode 2

    pla                         ; [4] (14)
    tax                         ; [2] (16) Restore X register
    pla                         ; [4] (20) Restore accumulator
    rti                         ; [6] (26) Return from interrupt

; ==============================================================================
; VBLANK ROUTINE — Runs during deferred vertical blank (Type 7)
; Resets initial DLI vector for the upcoming frame & updates time bar
; ==============================================================================
vblank_game
    lda #<dli_game_top
    sta VDSLST
    lda #>dli_game_top
    sta VDSLST+1

    ; Restore Player registers at start of frame
    lda dragon_x
    sta HPOSP0
    lda #0
    sta SIZEP0
    sta SIZEP1
    sta SIZEP2
    sta SIZEP3
    sta HPOSP1
    sta HPOSP2
    sta HPOSP3
    lda cur_sizem
    sta SIZEM
    lda cur_hposm0
    sta HPOSM0
    lda cur_hposm1
    sta HPOSM1
    lda cur_hposm2
    sta HPOSM2
    lda cur_hposm3
    sta HPOSM3
    sta ATRACT                  ; Reset OS Attract Mode timer (prevent color shift)
    lda pal_action_dragon
    sta COLPM0
    lda pal_action_p1
    sta COLPM1
    lda pal_action_p2
    sta COLPM2
    lda pal_action_p3
    sta COLPM3

    ; Check dragon collisions with playfield (PF0/1/2 = crash, PF3 = recharge)
    jsr check_dragon_collisions

    ; Check flame collision with world objects (destroys objects in path of fire)
    jsr check_flame_object_collision

    ; Update dragon energy bar counter during VBLANK (depletion)
    jsr update_energy_bar

    ; Update animated and rotated characters in GAME_FONT_ADDR ($7400)
    jsr animate_charset
    jsr update_animated_charset

    jmp XITVBV

; ==============================================================================
; init_energy_bar
; Initializes dragon energy bar in VRAM row 0: 39 full characters (82) + end (83)
; Resets COUNTER_FULL=40, COUNTER_EIGHT=83, energy_acc=0
; ==============================================================================
init_energy_bar
    lda #82
    ldx #38
@   sta GAME_STATUS_VRAM,x
    dex
    bpl @-
    lda #83
    sta GAME_STATUS_VRAM+39

    lda #40
    sta COUNTER_FULL
    lda #83                     ; End of bar starts at 83 (never 82!)
    sta COUNTER_EIGHT
    lda #0
    sta energy_acc_lo
    sta energy_acc_hi
    sta dragon_recharging
    rts

; ==============================================================================
; DRAGON ENERGY BAR UPDATE ROUTINE — Executed once per VBLANK
; Depletes dragon energy across 40 bar characters (each character animates codes 83..90)
; Total sub-steps = 40 * 8 = 320 steps.
; Base character: 82 (full bar), Animation: 83..90, Cleared: 0
; ==============================================================================
update_energy_bar
    lda GAME_OVER_REASON
    bne @tb_exit
    lda dragon_dying
    bne @tb_exit
    lda dragon_recharging
    bne @tb_exit

@tb_run

    ; Advance Bresenham accumulator by total bar steps (320 = 40 chars * 8 anim steps)
    lda energy_acc_lo
    clc
    adc #<320
    sta energy_acc_lo
    lda energy_acc_hi
    adc #>320
    sta energy_acc_hi

    ; Compare energy_acc with total energy frames
    lda energy_acc_lo
    cmp energy_frames_lo
    lda energy_acc_hi
    sbc energy_frames_hi
    bcc @tb_done            ; If energy_acc < energy_frames, not yet time to step

    ; energy_acc >= energy_frames: subtract energy_frames
    lda energy_acc_lo
    sec
    sbc energy_frames_lo
    sta energy_acc_lo
    lda energy_acc_hi
    sbc energy_frames_hi
    sta energy_acc_hi

    ; Safety check: if COUNTER_FULL is already 0, trigger death sequence
    lda COUNTER_FULL
    beq @tb_energy_empty

    ; Check if last character reached 90 (end of 8-character animation cycle)
    lda COUNTER_EIGHT
    cmp #90
    beq @tb_cycle_done

    ; Increment animation character code (83 -> 84 -> ... -> 90)
    inc COUNTER_EIGHT

@tb_draw
    ; On position (COUNTER_FULL - 1), display character = COUNTER_EIGHT (83..90)
    sec
    lda COUNTER_FULL
    sbc #1
    tax                     ; X = column 0..39
    lda COUNTER_EIGHT
    sta GAME_STATUS_VRAM,x
    rts

@tb_cycle_done
    ; When the end character finishes its 8 sub-steps:
    ; 1. Clear character at (COUNTER_FULL - 1)
    sec
    lda COUNTER_FULL
    sbc #1
    tax
    lda #0                  ; Empty space (cleared character)
    sta GAME_STATUS_VRAM,x

    ; 2. Decrement full bar character count
    dec COUNTER_FULL
    beq @tb_energy_empty    ; If 0, entire bar depleted -> Dragon runs out of energy!

    ; 3. Character 83 is placed at new end of bar (COUNTER_FULL - 1)
    lda #83
    sta COUNTER_EIGHT
    sec
    lda COUNTER_FULL
    sbc #1
    tax                     ; X = new end of bar
    lda #83
    sta GAME_STATUS_VRAM,x
    rts

@tb_energy_empty
    jsr start_dragon_death

@tb_done
@tb_exit
    rts

; ==============================================================================
; check_dragon_collisions
; Checks hardware GTIA Player 0 to Playfield collision (latched in dragon_p0pf).
; Playfield colors:
;   - Bit 0 (PF0), Bit 1 (PF1), Bit 2 (PF2): Wall/obstacle collision -> CRASH & DEATH!
;   - Bit 3 (PF3): Recharge color -> increases dragon energy by 1 step per frame.
; Background color (COLBK): Does not register in P0PF.
; ==============================================================================
.proc check_dragon_collisions
    ; Read latched collision mask captured in dli_game_bottom
    lda dragon_p0pf
    sta ZP_TMP
    lda #0
    sta dragon_p0pf

    ; If dragon is already dying or game over, skip collisions and cancel recharge
    lda dragon_dying
    bne @no_recharge
    lda GAME_OVER_REASON
    bne @no_recharge

    ; Test collision with PF0, PF1, or PF2 (bits 0, 1, 2)
    lda ZP_TMP
    and #$07
    beq @check_pf3

    ; Only crash if collision was with an active BLOCKING object (blocking == true)
    jsr check_dragon_blocking_collision
    bcc @check_pf3              ; Non-blocking object (or clear air) -> do not crash!

    ; Wall/obstacle collision: crash sound and death!
    lda #0
    sta dragon_recharging
    jsr start_dragon_crash
    rts

@check_pf3
    ; Test collision with PF3 (bit 3)
    lda ZP_TMP
    and #$08
    beq @no_recharge

    ; Recharging: increase energy by 1 step
    lda #1
    sta dragon_recharging
    jsr increase_energy_bar
    rts

@no_recharge
    lda #0
    sta dragon_recharging

@done
    rts
.endp

check_dragon_pf3_collision = check_dragon_collisions

; ==============================================================================
; increase_energy_bar
; Increases dragon energy by 1 sub-step (opposite of update_energy_bar depletion).
; If already at maximum (COUNTER_FULL=40, COUNTER_EIGHT<=83), does nothing.
; ==============================================================================
.proc increase_energy_bar
    ; Check if dragon is dying or game over
    lda dragon_dying
    bne @done
    lda GAME_OVER_REASON
    bne @done

    ; Safety check: if COUNTER_FULL is 0, bar is empty/dead
    lda COUNTER_FULL
    beq @done

    ; Check if already at maximum: COUNTER_FULL >= 40 and COUNTER_EIGHT <= 83
    cmp #40
    bcc @can_increase
    lda COUNTER_EIGHT
    cmp #84
    bcc @done                   ; If COUNTER_FULL >= 40 and COUNTER_EIGHT < 84 (<= 83), at maximum

@can_increase
    ; Reset fractional depletion accumulator so full step duration is given
    lda #0
    sta energy_acc_lo
    sta energy_acc_hi

    lda COUNTER_EIGHT
    cmp #83
    beq @advance_block

    ; Within current block: decrement COUNTER_EIGHT (90 -> 89 -> ... -> 83)
    dec COUNTER_EIGHT
    sec
    lda COUNTER_FULL
    sbc #1
    tax
    lda COUNTER_EIGHT
    sta GAME_STATUS_VRAM,x
    rts

@advance_block
    ; Current block at (COUNTER_FULL - 1) was at 83, so it becomes completely full (82)
    sec
    lda COUNTER_FULL
    sbc #1
    tax
    lda #82
    sta GAME_STATUS_VRAM,x

    ; Move to the next block to the right
    inc COUNTER_FULL
    lda #90
    sta COUNTER_EIGHT
    sec
    lda COUNTER_FULL
    sbc #1
    tax
    lda #90
    sta GAME_STATUS_VRAM,x

@done
    rts
.endp

; ==============================================================================
; start_dragon_death
; Initiates the ~2 second death sequence when dragon energy reaches zero.
; Controls are frozen, momentum stopped, fire breathing silenced.
; ==============================================================================
start_dragon_death
    lda dragon_dying
    bne @sdd_done               ; Already in dying sequence
    lda #DEATH_STATE_FADING     ; Phase 1: Fading & moving to left edge
    sta dragon_dying
    lda #DRAGON_DEATH_DURATION  ; 100 frames (~2 seconds @ 50Hz)
    sta death_timer
    lda #6
    sta death_move_timer

    ; Stop vertical velocity and horizontal scroll momentum
    lda #0
    sta dragon_vel_lo
    sta dragon_vel_hi
    sta SCROLL_SPEED
    sta SCROLL_SPEED+1

    ; Stop fire breath and silence POKEY
    sta fire_state
    sta fire_timer
    sta AUDC1
    sta AUDC2
@sdd_done
    rts

; ==============================================================================
; start_dragon_crash
; Initiates the crash sequence when dragon collides with PF0, PF1, or PF2.
; Halts movement, halts fire breathing, triggers crash sound and clears sprite.
; ==============================================================================
start_dragon_crash
    lda dragon_dying
    bne @sdc_done               ; Already in dying sequence

    lda #DEATH_STATE_CRASH      ; State 3: Wall collision crash
    sta dragon_dying
    lda #CRASH_DURATION         ; 24 frames (~0.5s @ 50Hz)
    sta death_timer

    ; Stop vertical velocity and horizontal scroll momentum immediately
    lda #0
    sta dragon_vel_lo
    sta dragon_vel_hi
    sta SCROLL_SPEED
    sta SCROLL_SPEED+1

    ; Stop fire breath and silence missile registers
    sta fire_state
    sta fire_timer
    sta dragon_recharging
    sta cur_sizem
    sta SIZEM
    sta HPOSM0
    sta HPOSM1
    sta HPOSM2
    sta HPOSM3
    sta cur_hposm0
    sta cur_hposm1
    sta cur_hposm2
    sta cur_hposm3

    ; Trigger frame 0 of crash sound
    ldx #0
    lda crash_snd_audf1,x
    sta AUDF1
    lda crash_snd_audc1,x
    sta AUDC1
    lda crash_snd_audf2,x
    sta AUDF2
    lda crash_snd_audc2,x
    sta AUDC2

@sdc_done
    rts

; ==============================================================================
; update_dragon_death
; Updates dragon death sequence once per frame when dragon_dying != 0.
; Phase 1 (DEATH_STATE_FADING):
;   - Moves dragon slowly leftwards to DRAGON_DEATH_TARGET_X (48)
;   - Fades dragon luminance from $C6 -> $C4 -> $C2 -> $C0
;   - When timer expires (X reaches 48 and luminance reaches 0):
;     Triggers explosion phase (sound & vaporize)!
; Phase 2 (DEATH_STATE_EXPLODING):
;   - Plays dual-channel POKEY explosion sound across 24 frames (~0.5s)
;   - When explosion finishes:
;     ONLY NOW decrements LIVES (or triggers Game Over if LIVES == 1)
; Phase 3 (DEATH_STATE_CRASH):
;   - Plays dual-channel POKEY crash sound across 24 frames (~0.5s)
;   - When crash finishes:
;     ONLY NOW decrements LIVES (or triggers Game Over if LIVES == 1)
; ==============================================================================
update_dragon_death
    lda dragon_dying
    cmp #DEATH_STATE_FADING
    beq @update_fade
    cmp #DEATH_STATE_EXPLODING
    beq @go_expl
    cmp #DEATH_STATE_CRASH
    bne @udd_done

@update_crash
    ; Play crash sound across 24 frames
    sec
    lda #CRASH_DURATION
    sbc death_timer             ; Index 0..23
    tax
    lda crash_snd_audf1,x
    sta AUDF1
    lda crash_snd_audc1,x
    sta AUDC1
    lda crash_snd_audf2,x
    sta AUDF2
    lda crash_snd_audc2,x
    sta AUDC2

    dec death_timer
    beq @crash_finished
@udd_done
    rts

@crash_finished
    jmp @death_finished

@go_expl
    jmp @update_expl

@update_fade
    ; 1. Move dragon leftwards towards DRAGON_DEATH_TARGET_X (48) every 6 frames
    dec death_move_timer
    bne @check_fade
    lda #6
    sta death_move_timer
    lda dragon_x
    cmp #DRAGON_DEATH_TARGET_X
    bcc @check_fade
    beq @check_fade
    dec dragon_x

@check_fade
    ; 2. Fade luminance based on death_timer (100 -> 0)
    lda death_timer
    cmp #75
    bcs @lum_6
    cmp #50
    bcs @lum_4
    cmp #25
    bcs @lum_2
    lda #$C0                    ; Luminance 0 (black silhouette)
    sta pal_action_dragon
    jmp @step_fade_timer

@lum_6
    lda #$C6                    ; Luminance 6 (full green)
    sta pal_action_dragon
    jmp @step_fade_timer

@lum_4
    lda #$C4                    ; Luminance 4
    sta pal_action_dragon
    jmp @step_fade_timer

@lum_2
    lda #$C2                    ; Luminance 2
    sta pal_action_dragon

@step_fade_timer
    dec death_timer
    bne @udd_done               ; Fading still in progress

    ; 3. Fading complete: dragon reached left edge and luminance is 0.
    ; Transition to Phase 2: EXPLOSION!
    lda #DRAGON_DEATH_TARGET_X
    sta dragon_x
    lda #$C0
    sta pal_action_dragon

    lda #DEATH_STATE_EXPLODING
    sta dragon_dying
    lda #EXPLOSION_DURATION
    sta death_timer

    ; Start frame 0 of explosion sound
    ldx #0
    lda expl_snd_audf1,x
    sta AUDF1
    lda expl_snd_audc1,x
    sta AUDC1
    lda expl_snd_audf2,x
    sta AUDF2
    lda expl_snd_audc2,x
    sta AUDC2
    rts

@update_expl
    ; Play explosion sound across 24 frames
    sec
    lda #EXPLOSION_DURATION
    sbc death_timer             ; Index 0..23
    tax
    lda expl_snd_audf1,x
    sta AUDF1
    lda expl_snd_audc1,x
    sta AUDC1
    lda expl_snd_audf2,x
    sta AUDF2
    lda expl_snd_audc2,x
    sta AUDC2

    dec death_timer
    bne @expl_done              ; Explosion still playing

@death_finished
    ; Explosion/Crash finished! Silence sound
    lda #0
    sta AUDC1
    sta AUDC2
    sta AUDF1
    sta AUDF2

    ; ONLY NOW (after sound finishes) check lives & decrement:
    lda LIVES
    cmp #1
    beq @out_of_lives

    ; LIVES > 1: decrement one life, update bottom status bar, and respawn dragon
    dec LIVES
    jsr update_bottom_status
    jsr respawn_dragon
    rts

@out_of_lives
    ; Already at 1 life: player is out of lives -> Game Over!
    lda #REASON_LIVES_OUT
    sta GAME_OVER_REASON

@expl_done
    rts

; ==============================================================================
; respawn_dragon
; Resets dragon position, state, full luminance, refills energy bar,
; and restarts the current level from the very beginning.
; Called when dragon died but player still has lives remaining.
; ==============================================================================
respawn_dragon
    lda #DEATH_STATE_INACTIVE
    sta dragon_dying
    sta dragon_recharging
    sta dragon_p0pf
    sta flame_m_pf
    sta death_timer
    sta death_move_timer
    sta HITCLR
    jsr init_flame_collision
    sta dragon_sub_y
    sta dragon_vel_lo
    sta dragon_vel_hi
    sta fire_state
    sta fire_frame
    sta fire_timer
    sta fire_prev_y
    sta AUDC1
    sta AUDC2
    sta AUDF1
    sta AUDF2
    sta AUDCTL
    sta HPOSM0
    sta HPOSM1
    sta HPOSM2
    sta HPOSM3
    sta SIZEM
    sta cur_hposm0
    sta cur_hposm1
    sta cur_hposm2
    sta cur_hposm3
    sta cur_sizem

    ; Reset horizontal scroll speed and momentum to base cruising speed
    lda #<SCROLL_BASE_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_BASE_SPEED
    sta SCROLL_SPEED+1

    ; Reset animation phase and speed
    lda #0
    sta ANIM_PHASE
    sta ANIM_PHASE+1
    jsr update_anim_speed

    ; Reset dragon coordinates
    lda #DRAGON_START_X
    sta dragon_x
    sta HPOSP0
    lda #DRAGON_START_Y
    sta dragon_y
    sta dragon_prev_y

    lda #DRAGON_COLOR
    sta pal_action_dragon

    ; Restart current level from the very beginning (screen 0, hscrol_fine=3, reset buffers)
    jsr init_level_screens

    ; Refill dragon energy bar in VRAM and reset counters
    jsr init_energy_bar
    jsr calc_energy_frames

    ; Re-render dragon in respawned position
    jsr render_dragon
    rts

; ==============================================================================
; calc_energy_frames
; Calculates 16-bit total frame count for dragon energy:
; energy_frames = dragon_energy_sec * frames_per_second
; PAL (50Hz):  30 * 50 = 1500 frames ($05DC)
; NTSC (60Hz): 30 * 60 = 1800 frames ($0708)
; ==============================================================================
calc_energy_frames
    lda PAL
    and #$08
    bne @is_ntsc
    ; PAL (50Hz)
    lda #50
    sta calc_fps_sec
    jmp @setup_fps

@is_ntsc
    ; NTSC (60Hz)
    lda #60
    sta calc_fps_sec

@setup_fps
    lda #0
    sta energy_frames_lo
    sta energy_frames_hi

    lda dragon_energy_sec
    beq @calc_energy_done
    sta calc_temp

@sec_loop
    clc
    lda energy_frames_lo
    adc calc_fps_sec
    sta energy_frames_lo
    lda energy_frames_hi
    adc #0
    sta energy_frames_hi
    dec calc_temp
    bne @sec_loop

@calc_energy_done
    ; Safety check: ensure at least 320 frames
    lda energy_frames_hi
    bne @calc_energy_ok
    lda energy_frames_lo
    cmp #<320
    bcs @calc_energy_ok
    lda #<320
    sta energy_frames_lo
    lda #>320
    sta energy_frames_hi
@calc_energy_ok
    rts

; ==============================================================================
; ==============================================================================
; LOAD_WORLD_SCREEN — Loads 440-byte screen buffer into visible cols 4..43 of GAME_ACTION_VRAM (48-byte rows)
; Input: X = screen index (0..WORLD_SCREENS_COUNT-1)
; Clobbers: A, X, Y, PTR_SRC ($80/$81), PTR_DST ($82/$83)
; ==============================================================================
load_world_screen
    cpx #WORLD_SCREENS_COUNT
    bcc @valid_screen
    ldx #0
@valid_screen
    stx current_screen_idx

    lda screens_vram_lo,x
    sta PTR_SRC
    lda screens_vram_hi,x
    sta PTR_SRC+1

    lda #<GAME_ACTION_VRAM
    sta PTR_DST
    lda #>GAME_ACTION_VRAM
    sta PTR_DST+1

    ldx #0                      ; Row counter (0..10)
@lws_row_loop
    ldy #0
@lws_col_loop
    lda (PTR_SRC),y
    pha
    tya
    clc
    adc #4
    tay
    pla
    sta (PTR_DST),y
    tya
    sec
    sbc #4
    tay
    iny
    cpy #40
    bne @lws_col_loop

    ; Duplicate col 0 into col 3 (for smooth left edge at HSCROL=3)
    ldy #0
    lda (PTR_SRC),y
    ldy #3
    sta (PTR_DST),y

    ; Advance PTR_SRC by 40
    lda PTR_SRC
    clc
    adc #40
    sta PTR_SRC
    bcc @lws_src_no_c
    inc PTR_SRC+1
@lws_src_no_c

    ; Advance PTR_DST by 48
    lda PTR_DST
    clc
    adc #48
    sta PTR_DST
    bcc @lws_dst_no_c
    inc PTR_DST+1
@lws_dst_no_c

    inx
    cpx #11
    bne @lws_row_loop
    rts

; Compatibility aliases
update_time_bar     = update_energy_bar
calc_stage_frames   = calc_energy_frames

; ==============================================================================
; WORLD STREAMING & PLAYFIELD SCROLLING SUBROUTINES (ANTIC HSCROL)
; ==============================================================================

init_level_screens
    lda #0
    sta level_screen_pos
    sta incoming_col_idx
    sta level_tail_cols
    sta scroll_accum_lo
    sta scroll_accum_hi
    lda #3
    sta hscrol_fine

    ; Fetch total screens count for current_level_idx
    ldx current_level_idx
    lda labyrinths_screen_count,x
    sta lab_total_screens

    ; Clear entire 528 bytes of GAME_ACTION_VRAM ($6000..$620F)
    ldx #0
    lda #0
@clr_vram_loop
    sta GAME_ACTION_VRAM,x
    sta GAME_ACTION_VRAM + 256,x
    inx
    bne @clr_vram_loop
    ldx #15
@clr_vram_tail
    sta GAME_ACTION_VRAM + 512,x
    dex
    bpl @clr_vram_tail

    ; Load screen 0 of this labyrinth into cols 4..43
    jsr setup_incoming_screen_ptr
    jsr load_world_screen
    jsr init_blocking_cols

    ; Check if labyrinth has a screen 1
    lda lab_total_screens
    cmp #2
    bcc @init_single_screen

    ; Advance level_screen_pos to 1 for incoming stream
    inc level_screen_pos
    jsr setup_incoming_screen_ptr

    ; Prefill right margin (cols 44..47) with cols 0..3 of screen 1
    lda incoming_screen_ptr
    sta PTR_SRC
    lda incoming_screen_ptr+1
    sta PTR_SRC+1

    lda #<GAME_ACTION_VRAM
    sta PTR_DST
    lda #>GAME_ACTION_VRAM
    sta PTR_DST+1

    ldx #0
@prefill_right_loop
    ldy #0
    lda (PTR_SRC),y
    ldy #44
    sta (PTR_DST),y
    ldy #1
    lda (PTR_SRC),y
    ldy #45
    sta (PTR_DST),y
    ldy #2
    lda (PTR_SRC),y
    ldy #46
    sta (PTR_DST),y
    ldy #3
    lda (PTR_SRC),y
    ldy #47
    sta (PTR_DST),y

    ; Advance PTR_SRC by 40
    lda PTR_SRC
    clc
    adc #40
    sta PTR_SRC
    bcc @pfr_src_no_c
    inc PTR_SRC+1
@pfr_src_no_c

    ; Advance PTR_DST by 48
    lda PTR_DST
    clc
    adc #48
    sta PTR_DST
    bcc @pfr_dst_no_c
    inc PTR_DST+1
@pfr_dst_no_c

    inx
    cpx #11
    bne @prefill_right_loop

    ; Next incoming column to stream is col 4
    lda #4
    sta incoming_col_idx
    rts

@init_single_screen
    ; Only 1 screen: enter tail mode immediately
    lda #48
    sta level_tail_cols
    lda #0
    sta incoming_col_idx
    rts

setup_incoming_screen_ptr
    ldx current_level_idx
    lda labyrinths_screens_lo,x
    sta PTR_SRC
    lda labyrinths_screens_hi,x
    sta PTR_SRC+1

    ldy level_screen_pos
    lda (PTR_SRC),y
    tax                         ; X = screen index (0..WORLD_SCREENS_COUNT-1)
    lda screens_vram_lo,x
    sta incoming_screen_ptr
    lda screens_vram_hi,x
    sta incoming_screen_ptr+1
    rts

update_world_scrolling
    ; Accumulate speed (8.8 fixed-point: $0100 = 1 color clock)
    lda scroll_accum_lo
    clc
    adc SCROLL_SPEED
    sta scroll_accum_lo
    lda scroll_accum_hi
    adc SCROLL_SPEED+1
    sta scroll_accum_hi

    ; Check if coarse threshold ($0400 = 4 color clocks = 1 char) reached
    cmp #>SCROLL_COL_THRESHOLD
    bcc @calc_fine_scroll
    bne @do_coarse_shift
    lda scroll_accum_lo
    cmp #<SCROLL_COL_THRESHOLD
    bcc @calc_fine_scroll

@do_coarse_shift
    ; Subtract threshold ($0400) from accumulator
    lda scroll_accum_lo
    sec
    sbc #<SCROLL_COL_THRESHOLD
    sta scroll_accum_lo
    lda scroll_accum_hi
    sbc #>SCROLL_COL_THRESHOLD
    sta scroll_accum_hi

    ; Execute coarse scroll: shift 48-byte VRAM left and stream new byte into col 47
    jsr scroll_playfield_step

@calc_fine_scroll
    ; Compute fine scroll value for HSCROL:
    ; In ANTIC Mode 5, fine scroll is 0..3 color clocks.
    ; Moving left means HSCROL steps 3 -> 2 -> 1 -> 0
    ; hscrol_fine = 3 - (scroll_accum_hi & 3)
    lda scroll_accum_hi
    and #$03
    sta ZP_TMP
    lda #3
    sec
    sbc ZP_TMP
    sta hscrol_fine
    rts

shift_vram_left
    ldx #0
@shift_vram_loop
    lda GAME_ACTION_VRAM + 1,x
    sta GAME_ACTION_VRAM,x
    lda GAME_ACTION_VRAM + 49,x
    sta GAME_ACTION_VRAM + 48,x
    lda GAME_ACTION_VRAM + 97,x
    sta GAME_ACTION_VRAM + 96,x
    lda GAME_ACTION_VRAM + 145,x
    sta GAME_ACTION_VRAM + 144,x
    lda GAME_ACTION_VRAM + 193,x
    sta GAME_ACTION_VRAM + 192,x
    lda GAME_ACTION_VRAM + 241,x
    sta GAME_ACTION_VRAM + 240,x
    lda GAME_ACTION_VRAM + 289,x
    sta GAME_ACTION_VRAM + 288,x
    lda GAME_ACTION_VRAM + 337,x
    sta GAME_ACTION_VRAM + 336,x
    lda GAME_ACTION_VRAM + 385,x
    sta GAME_ACTION_VRAM + 384,x
    lda GAME_ACTION_VRAM + 433,x
    sta GAME_ACTION_VRAM + 432,x
    lda GAME_ACTION_VRAM + 481,x
    sta GAME_ACTION_VRAM + 480,x
    inx
    cpx #47
    bne @shift_vram_loop
    rts

scroll_playfield_step
    jsr shift_vram_left
    jsr shift_blocking_cols

    lda level_tail_cols
    beq @stream_screen_col

    ; Tail mode: blank rightmost column ($00)
    lda #0
    sta GAME_ACTION_VRAM + 47
    sta GAME_ACTION_VRAM + 95
    sta GAME_ACTION_VRAM + 143
    sta GAME_ACTION_VRAM + 191
    sta GAME_ACTION_VRAM + 239
    sta GAME_ACTION_VRAM + 287
    sta GAME_ACTION_VRAM + 335
    sta GAME_ACTION_VRAM + 383
    sta GAME_ACTION_VRAM + 431
    sta GAME_ACTION_VRAM + 479
    sta GAME_ACTION_VRAM + 527

    dec level_tail_cols
    bne @tail_not_done

    ; Tail completed: all screens in this level cleared!
    jsr advance_to_next_level
@tail_not_done
    rts

@stream_screen_col
    lda incoming_screen_ptr
    sta PTR_SRC
    lda incoming_screen_ptr+1
    sta PTR_SRC+1

    ; Rows 0..5 (offsets 0..239 in source screen buffer)
    ldy incoming_col_idx
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 47

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 95

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 143

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 191

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 239

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 287

    ; Rows 6..10 (advance PTR_SRC by 240)
    lda PTR_SRC
    clc
    adc #240
    sta PTR_SRC
    bcc @ptr_no_c
    inc PTR_SRC+1
@ptr_no_c
    ldy incoming_col_idx
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 335

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 383

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 431

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 479

    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta GAME_ACTION_VRAM + 527

    ; Advance incoming_col_idx
    inc incoming_col_idx
    lda incoming_col_idx
    cmp #40
    bcc @step_rts

    ; Current screen completely streamed in (columns 0..39 finished)
    lda #0
    sta incoming_col_idx

    inc level_screen_pos
    lda level_screen_pos
    cmp lab_total_screens
    bcc @next_screen_in_lab

    ; All screens in this level streamed -> enter 48 cols tail mode
    lda #48
    sta level_tail_cols
    rts

@next_screen_in_lab
    jsr setup_incoming_screen_ptr

@step_rts
    rts

advance_to_next_level
    inc current_level_idx
    lda current_level_idx
    cmp #WORLD_LABYRINTHS_COUNT
    bcc @have_another_level

    ; All labyrinths completed! Transition to Game Over with SUCCESS
    lda #REASON_SUCCESS
    sta GAME_OVER_REASON
    rts

@have_another_level
    inc LEVEL
    jsr update_bottom_status
    jsr init_level_screens
    rts

; --- Playfield Horizontal Scrolling & World Streaming Variables ---
current_level_idx   dta 0           ; Index of current labyrinth (0..WORLD_LABYRINTHS_COUNT-1)
level_screen_pos    dta 0           ; Position within current labyrinth (0..lab_total_screens-1)
lab_total_screens   dta 0           ; Total number of screens in current labyrinth
incoming_col_idx    dta 0           ; Column index (0..39) currently streaming from screen buffer
level_tail_cols     dta 0           ; Countdown of tail empty columns (48..0) after last screen
scroll_accum_lo     dta 0           ; 16-bit scroll sub-pixel accumulator (low byte)
scroll_accum_hi     dta 0           ; 16-bit scroll sub-pixel accumulator (high byte)
hscrol_fine         dta 3           ; Fine horizontal scroll value (0..3 color clocks) for HSCROL ($D404)
incoming_screen_ptr dta a(0)        ; 16-bit pointer to currently streaming screen's VRAM buffer

calc_fps_sec        dta 0
calc_temp           dta 0
current_screen_idx  dta 0

; ==============================================================================
; PALETTE CONFIGURATION CELLS (editable during development / tuning)
; All colors used across the game screen and DLI interrupts
; ==============================================================================

; --- Action Screen Palette (set in dli_game_action & game_init) ---
pal_action_dragon   dta $C6         ; COLPM0: Smok (Player 0) - domyślnie zielony (Hue $C, Lum 6)
pal_action_breath   dta 130         ; COLPF3: Zianie ogniem / pociski / PF3_INV (colors.yaml: 130)
pal_action_bk       dta 0           ; COLBK:  Tło ekranu akcji i ramka (colors.yaml: 0)
pal_action_pf0      dta 20          ; COLPF0: Pole gry 0 (colors.yaml: 20)
pal_action_pf1      dta 24          ; COLPF1: Pole gry 1 (colors.yaml: 24)
pal_action_pf2      dta 194         ; COLPF2: Pole gry 2 (colors.yaml: 194)
pal_action_p1       dta $36         ; COLPM1: Gracz 1 (np. pociski wroga) - czerwony
pal_action_p2       dta $28         ; COLPM2: Gracz 2 - złoty
pal_action_p3       dta $1A         ; COLPM3: Gracz 3 - jasnożółty

; --- Top Status Bar Palette (dli_game_top, normal text) ---
pal_top_bar         dta $02, $04, $06, $08, $08, $06, $04, $02 ; COLPF1: Pasek energii smoka (color bar gradient 8 scanlines)
pal_top_text        dta $0A         ; COLPF1: Domyślny kolor tekstu (legacy)
pal_top_bk          dta $70         ; COLPF2: Tło górnej linii - niebieski

; --- Bottom Status Bar Palette (dli_game_bottom, normal text) ---
pal_bottom_bar      dta $06, $08, $0a, $0c, $0c, $0a, $08, $06 ; COLPF1: Dolny pasek (color bar gradient 8 scanlines)
pal_bottom_text     dta $0A         ; COLPF1: Domyślny kolor tekstu (legacy)
pal_bottom_bk       dta $30         ; COLPF2: Tło dolnej linii - fioletowy

; --- Bottom Status Bar Sprite Overlay Configuration ---
bot_bar_p0_x        dta BOTTOM_BAR_P0_X ; Pozycja X Sprite 0 (48: "LEVEL:01")
bot_bar_p1_x        dta 88              ; Pozycja X Sprite 1 (88: "SCORE:")
bot_bar_m_x         dta BOTTOM_BAR_M_X  ; Pozycja X Missile 1 (120: dwa ostatnie zera SCORE "00")
bot_bar_p2_x        dta 136             ; Pozycja X Sprite 2 (136: "LIVES:03")
bot_bar_p3_x        dta 176             ; Pozycja X Sprite 3 (176: "SHOTS:01")
bot_bar_pmg_y       dta 220           ; Pozycja pionowa Y paska PMG (indeks linii 0..255 w buforze)
pal_bottom_p0       dta $A0             ; Kolor Sprite 0 (cyan)
pal_bottom_p1       dta $90             ; Kolor Sprite 1 (blue-cyan)
pal_bottom_m        dta $90             ; Kolor Missile 1 (blue-cyan - dopasowany do SCORE)
pal_bottom_p2       dta $10             ; Kolor Sprite 2 (żółty)
pal_bottom_p3       dta $20             ; Kolor Sprite 3 (ognisty pomarańczowy / fire orange)

; --- Active Fire Missiles Shadow Registers ---
cur_hposm0          dta 0
cur_hposm1          dta 0
cur_hposm2          dta 0
cur_hposm3          dta 0
cur_sizem           dta 0

; --- Dragon Energy & Game Over State ---
COUNTER_FULL        dta 40          ; Remaining characters on the energy bar (40..0)
COUNTER_EIGHT       dta 83          ; Current animation character code at end of bar (strictly 83..90)
GAME_OVER_REASON    dta 0           ; Reason game ended
energy_acc_lo       dta 0           ; 16-bit Bresenham energy accumulator low
energy_acc_hi       dta 0           ; 16-bit Bresenham energy accumulator high
time_acc_lo         = energy_acc_lo ; Compatibility alias
time_acc_hi         = energy_acc_hi ; Compatibility alias

; --- Dragon Energy Configuration (upgradeable during gameplay) ---
DRAGON_INITIAL_ENERGY_SEC = 30      ; Initial dragon flight energy duration in seconds (~30s)
dragon_energy_sec   dta DRAGON_INITIAL_ENERGY_SEC ; Current energy capacity in seconds (upgradeable)

; Frame duration for dragon energy depletion (computed at runtime by calc_energy_frames)
energy_frames_lo    dta <1500
energy_frames_hi    dta >1500
stage_frames_lo     = energy_frames_lo ; Compatibility alias
stage_frames_hi     = energy_frames_hi ; Compatibility alias

; --- Game Status & Score Variables ---
LEVEL               dta 1           ; Current level (1 byte, 1..255)
LIVES               dta 3           ; Remaining lives (1 byte, 0..255)
SCORE               dta 0, 0, 0, 0  ; Score: 4 decimal digits (each 0..9)
SHOTS               dta 1           ; Dragon fire shots (1 byte, 0..255, initial: 1)

; --- Bottom Status Bar Blinking State ---
LIVES_BLINK_PERIOD  = 25            ; 25 frames = 0.5s @ 50Hz (half second)
lives_blink_timer   dta 25
lives_blink_state   dta 0           ; 0 = visible ('1'), 1 = blanked (' ')

; Game Over Reason Constants
REASON_NONE         = 0
REASON_ENERGY_EMPTY = 1             ; Energia smoka wyczerpana
REASON_TIME_UP      = 1             ; Compatibility alias
REASON_LIVES_OUT    = 2             ; Skończyły się życia
REASON_PLAYER_QUIT  = 3             ; Gracz zakończył grę (START)
REASON_SUCCESS      = 4             ; Sukces - ukończone wszystkie poziomy

status_line_lo
    dta <GAME_STATUS_VRAM, <(GAME_STATUS_VRAM + 40)

; --- Dragon State Variables ---
dragon_x            dta DRAGON_START_X
dragon_y            dta DRAGON_START_Y
dragon_prev_y       dta DRAGON_START_Y
dragon_sub_y        dta 0
dragon_vel_lo       dta 0
dragon_vel_hi       dta 0

; --- Dragon Death State Variables ---
dragon_dying        dta 0           ; 0 = active/controllable, 1 = dying sequence
dragon_recharging   dta 0           ; 0 = normal, 1 = recharging via PF3 collision
dragon_p0pf         dta 0           ; Latched P0PF collision register from action area
death_timer         dta 0           ; Countdown timer for 2s death sequence (100..0)
death_move_timer    dta 0           ; Sub-frame timer for horizontal shift (6..1)


; --- Fire Breathing State Variables ---
fire_state          dta 0           ; 0 = inactive, 1 = expanding, 2 = peak, 3 = retracting
fire_frame          dta 0           ; Frame 0..7
fire_timer          dta 0           ; Countdown timer in frames
fire_prev_y         dta 0           ; Previous scanline Y rendered in M_ADDR

; --- Fire Animation & Geometry Tables (8 frames) ---
; Ease-in durations: Frame 0 longest (7 frames), Frame 6 shortest (1 frame)
fire_duration_tbl
    dta 7, 5, 4, 3, 2, 2, 1, 2

; --- Fire Breath Sound Tables (POKEY Channels 1 & 2 across 8 frames) ---
fire_snd_audf1      dta $3C, $34, $2C, $24, $20, $1C, $1A, $18 ; Ch 1 Pitch (lower = deeper roar)
fire_snd_audc1      dta $04, $06, $08, $0A, $0C, $0D, $0E, $0F ; Ch 1 Volume (distortion $00 = complex noise)
fire_snd_audf2      dta $30, $28, $20, $1C, $18, $16, $14, $12 ; Ch 2 Pitch (white noise rate)
fire_snd_audc2      dta $83, $85, $87, $89, $8B, $8C, $8D, $8E ; Ch 2 Volume (distortion $80 = white noise hiss)

; SIZEM: 2-bits per missile (M3..M0): $00, $01, $05, $07, $17, $1F, $5F, $7F
fire_sizem_tbl
    dta $00, $01, $05, $07, $17, $1F, $5F, $7F

; Horizontal offsets from dragon_x for M0..M3 (0 = inactive/offscreen)
fire_off_m0
    dta 8, 8, 8, 8, 8, 8, 8, 8
fire_off_m1
    dta 0, 12, 12, 16, 16, 16, 16, 16
fire_off_m2
    dta 0, 0, 16, 20, 20, 24, 24, 24
fire_off_m3
    dta 0, 0, 0, 0, 24, 28, 28, 32

; Pattern byte offset per frame (7 bytes per frame)
fire_pattern_idx
    dta 0, 7, 14, 21, 28, 35, 42, 49

; 7 scanlines per frame (M3=bits 7-6, M2=bits 5-4, M1=bits 3-2, M0=bits 1-0)
fire_pattern_data
    ; Frame 0: tiny spark at mouth (~1 line height)
    dta %00000000
    dta %00000000
    dta %00000000
    dta %00000011
    dta %00000000
    dta %00000000
    dta %00000000

    ; Frame 1: M0 2x, M1 emerging (~2-3 lines height)
    dta %00000000
    dta %00000000
    dta %00000101
    dta %00001111
    dta %00000110
    dta %00000000
    dta %00000000

    ; Frame 2: M0 2x, M1 2x, M2 emerging (~3 lines height)
    dta %00000000
    dta %00000000
    dta %00011101
    dta %00111111
    dta %00011110
    dta %00000000
    dta %00000000

    ; Frame 3: M0 4x, M1 2x, M2 1x (~4 lines height)
    dta %00000000
    dta %00010100
    dta %00111101
    dta %00111111
    dta %00111111
    dta %00010100
    dta %00000000

    ; Frame 4: M0 4x, M1 2x, M2 2x, M3 emerging (~5 lines height)
    dta %00000000
    dta %01110100
    dta %11111101
    dta %11111111
    dta %11111110
    dta %01110100
    dta %00000000

    ; Frame 5: M0 4x, M1 4x, M2 2x, M3 1x (~6 lines height)
    dta %01010000
    dta %11110100
    dta %11111101
    dta %11111111
    dta %11111111
    dta %11111100
    dta %01010000

    ; Frame 6: M0 4x, M1 4x, M2 2x, M3 2x (flickering flame tongue, ~7 lines)
    dta %01100000
    dta %11110100
    dta %10111101
    dta %11111111
    dta %11111110
    dta %11111100
    dta %10010000

    ; Frame 7: Full flame tongue, organic jagged edges (7 lines height)
    dta %10110000
    dta %11110100
    dta %11111101
    dta %11111111
    dta %11111111
    dta %11111101
    dta %01110000

; --- 16-bit Animation & Scroll Variables ---
ANIM_PHASE          dta a(0)        ; 16-bit Phase Accumulator: low=fraction, high=frame (0..5)
ANIM_SPEED          dta a(BASE_HOVER_SPEED) ; 16-bit Animation rate: BASE_HOVER_SPEED + (SCROLL_SPEED / 4)
SCROLL_SPEED        dta a(0)        ; 16-bit Horizontal scroll speed (8.8 fixed-point)

; --- Status Bar Text Data (ANTIC display codes) ---
status_bottom_txt
    dta 40, d'LEVEL:01  SCORE:0000  LIVES:03  SHOTS:01'
