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
SCROLL_ACCEL            = $0010         ; Scroll acceleration rate when holding Right
SCROLL_BRAKE            = $0024         ; Scroll braking rate when holding Left
SCROLL_DRAG             = $0006         ; Momentum decay towards hover when neutral

game_init
    ; Blank DMA during reconfiguration
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset PMG
    jsr disable_pmg

    ; Clear Player 0, 1, 2 buffers ($2400-$26FF) and Missiles ($2300-$23FF)
    ldx #0
    lda #0
@   sta P0_ADDR,x
    sta P1_ADDR,x
    sta P2_ADDR,x
    sta M_ADDR,x
    inx
    bne @-

    ; Fill 8 lines of Player 0, 1, 2 with $FF for bottom status bar overlay
    ldx bot_bar_pmg_y
    ldy #7
    lda #$FF
@fill_p_bot
    sta P0_ADDR,x
    sta P1_ADDR,x
    sta P2_ADDR,x
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
    sta SCROLL_SPEED
    sta SCROLL_SPEED+1

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

    ; Initialize hardware and shadow color registers from palette memory cells
    lda pal_action_pf0
    sta COLOR0
    sta COLPF0
    lda pal_action_pf1
    sta COLOR1
    sta COLPF1
    lda pal_action_pf2
    sta COLOR2
    sta COLPF2
    lda pal_action_breath
    sta COLOR3
    sta COLPF3
    lda pal_action_bk
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

    ; Clear 440 bytes of action playfield ($6000-$61B7) with empty tiles (0)
    lda #0
    ldx #0
@   sta GAME_ACTION_VRAM,x
    cpx #440-256        ; 184 ($B8)
    bcs @+
    sta GAME_ACTION_VRAM+256,x
@   inx
    bne @-1

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

    ; Initialize time bar (row 0): 39 full characters (82) + end of bar (83)
    ; The end of the bar NEVER has character 82; it always displays 83..90!
    lda #82
    ldx #38
@   sta GAME_STATUS_VRAM,x
    dex
    bpl @-
    lda #83
    sta GAME_STATUS_VRAM+39

    ; Initialize time bar counters & game over reason
    lda #40
    sta COUNTER_FULL
    lda #83                     ; End of bar starts at 83 (never 82!)
    sta COUNTER_EIGHT
    lda #0
    sta GAME_OVER_REASON
    sta time_acc_lo
    sta time_acc_hi

    ; Compute stage frame counts based on stage1..3_min/sec and PAL/NTSC detection
    jsr calc_stage_frames
    ; Initialize game status values (LEVEL, LIVES, SCORE)
    lda #1
    sta LEVEL
    lda #3
    sta LIVES
    lda #0
    ldx #5
@init_score
    sta SCORE,x
    dex
    bpl @init_score

    ; Draw initial bottom status bar (row 1)
    jsr draw_bottom_status

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
    ; 1. Check if time ran out
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
    ; 2. Check FIRE button to trigger fire breathing
    lda fire_pressed
    beq @not_fire
    lda #0
    sta fire_pressed
    lda fire_state
    bne @not_fire           ; If already firing, ignore subsequent press
    jsr start_fire

@not_fire
    ; Reset OS Attract Mode timer to prevent color shifting during gameplay
    lda #0
    sta ATRACT

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
    bcc @scroll_updated
    lda #<SCROLL_MAX_SPEED
    sta SCROLL_SPEED
    lda #>SCROLL_MAX_SPEED
    sta SCROLL_SPEED+1
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
    bpl @scroll_updated
    lda #0
    sta SCROLL_SPEED
    sta SCROLL_SPEED+1
    jmp @scroll_updated

@scroll_neutral
    ; Neither Left nor Right held -> Coasting / momentum decay towards 0
    lda SCROLL_SPEED+1
    bne @apply_scroll_drag
    lda SCROLL_SPEED
    beq @scroll_updated             ; Already 0 (stationary base hover)

@apply_scroll_drag
    lda SCROLL_SPEED
    sec
    sbc #<SCROLL_DRAG
    sta SCROLL_SPEED
    lda SCROLL_SPEED+1
    sbc #>SCROLL_DRAG
    sta SCROLL_SPEED+1
    bpl @scroll_updated
    lda #0
    sta SCROLL_SPEED
    sta SCROLL_SPEED+1

@scroll_updated
    ; 4. Recalculate dynamic ANIM_SPEED = BASE_HOVER_SPEED + (SCROLL_SPEED / 4)
    jsr update_anim_speed

    ; Update bottom status bar display
    jsr update_bottom_status

    ; Update fire breathing animation & sound
    jsr update_fire
    jsr update_fire_sound

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

    ; Ensure bottom status bar overlay stays $FF for Players 0, 1, 2
    ldx bot_bar_pmg_y
    ldy #7
    lda #$FF
@keep_p_bot
    sta P0_ADDR,x
    sta P1_ADDR,x
    sta P2_ADDR,x
    inx
    dey
    bpl @keep_p_bot
    rts

; ==============================================================================
; BOTTOM STATUS BAR SYSTEM
; Displays LEVEL, SCORE (6 digits), and LIVES on status bar row 1
; Layout: " LEVEL: 1     SCORE: 000000    LIVES: 3 " (40 chars)
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
    ; Update LEVEL digit (column 8)
    lda LEVEL
    cmp #10
    bcc @lvl_single
    ldx #0
@div10
    sec
    sbc #10
    inx
    cmp #10
    bcs @div10
    tay
    txa
    clc
    adc #$90
    sta GAME_STATUS_VRAM + 48
    tya
    clc
    adc #$90
    sta GAME_STATUS_VRAM + 49
    jmp @lvl_done
@lvl_single
    clc
    adc #$90
    sta GAME_STATUS_VRAM + 48
    lda #$80                    ; Blank space after single digit
    sta GAME_STATUS_VRAM + 49
@lvl_done

    ; Update SCORE 6 digits (columns 21..26)
    ldx #0
@score_loop
    lda SCORE,x
    clc
    adc #$90
    sta GAME_STATUS_VRAM + 61,x
    inx
    cpx #6
    bne @score_loop

    ; Update LIVES digit (column 38)
    lda LIVES
    clc
    adc #$90
    sta GAME_STATUS_VRAM + 78
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
    sta SIZEM

    ; Compute and set HPOSM0..3 = dragon_x + offset (or 0 if inactive)
    lda fire_off_m0,x
    beq @m0_off
    clc
    adc dragon_x
@m0_off
    sta HPOSM0

    lda fire_off_m1,x
    beq @m1_off
    clc
    adc dragon_x
@m1_off
    sta HPOSM1

    lda fire_off_m2,x
    beq @m2_off
    clc
    adc dragon_x
@m2_off
    sta HPOSM2

    lda fire_off_m3,x
    beq @m3_off
    clc
    adc dragon_x
@m3_off
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

    lda pal_top_bk              ; [4] (12) Top status background: blue
    sta COLPF2                  ; [4] (16) In Mode 2 (normal text): COLPF2 = background
    lda #<dli_game_action       ; [2] (18) Chain to DLI 2 (restore action palette)
    sta VDSLST                  ; [4] (22)
    lda #>dli_game_action       ; [2] (24)
    sta VDSLST+1                ; [4] (28)

    ldx #0                      ; [2] (30) Initialize scanline index (0..7)
@top_bar_loop
    lda pal_top_bar,x           ; [4] (34) Load color value for current scanline
    sta WSYNC                   ; [4] (38) Wait for horizontal sync
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

    ; Restore Player 0 hardware registers for dragon & disable P1/P2 in action area
    lda dragon_x                ; [4] (11) Player 0 position
    sta HPOSP0                  ; [4] (15)
    lda #0                      ; [2] (17) Normal width (1x) & offscreen for unused sprites
    sta SIZEP0                  ; [4] (21)
    sta SIZEP1                  ; [4] (25)
    sta SIZEP2                  ; [4] (29)
    sta HPOSP1                  ; [4] (33) Inactive in action area
    sta HPOSP2                  ; [4] (37) Inactive in action area

    ; Restore entire action playfield palette from memory cells
    lda pal_action_dragon       ; [4] (25) Player 0: Dragon body
    sta COLPM0                  ; [4] (29)
    lda pal_action_breath       ; [4] (33) Missiles (5th player): Dragon breath / flame
    sta COLPF3                  ; [4] (37)
    lda pal_action_pf0          ; [4] (41) Playfield color 0
    sta COLPF0                  ; [4] (45)
    lda pal_action_pf1          ; [4] (49) Playfield color 1
    sta COLPF1                  ; [4] (53)
    lda pal_action_pf2          ; [4] (57) Playfield color 2
    sta COLPF2                  ; [4] (61)
    lda pal_action_bk           ; [4] (65) Background color & border
    sta COLBK                   ; [4] (69)

    lda #<dli_game_bottom       ; [2] (71) Chain to DLI 3 (bottom status)
    sta VDSLST                  ; [4] (75)
    lda #>dli_game_bottom       ; [2] (77)
    sta VDSLST+1                ; [4] (81)
    pla                         ; [4] (85) Restore accumulator
    rti                         ; [6] (91) Return from interrupt

dli_game_bottom
    pha                         ; [3] (3) Save accumulator
    txa                         ; [2] (5)
    pha                         ; [3] (8) Save X register

    lda pal_bottom_bk           ; [4] (12) Bottom status background: black/purple
    sta COLPF2                  ; [4] (16) In Mode 2 (normal text): COLPF2 = background
    lda #<dli_game_top          ; [2] (18) Reset DLI vector to top handler for next frame
    sta VDSLST                  ; [4] (22)
    lda #>dli_game_top          ; [2] (24)
    sta VDSLST+1                ; [4] (28)

    ; Reconfigure Players 0, 1, 2 for bottom status overlay (x4 width)
    lda bot_bar_p0_x            ; [4] (30) Left edge of playfield (48 / $30)
    sta HPOSP0                  ; [4] (34)
    lda bot_bar_p1_x            ; [4] (38) Centered for "SCORE:"
    sta HPOSP1                  ; [4] (42)
    lda bot_bar_p2_x            ; [4] (46) Right side for "LIVES:"
    sta HPOSP2                  ; [4] (50)

    lda #3                      ; [2] (52) Quadruple width (x4)
    sta SIZEP0                  ; [4] (56)
    sta SIZEP1                  ; [4] (60)
    sta SIZEP2                  ; [4] (64)

    lda pal_bottom_p0           ; [4] (68) Color P0 (black)
    sta COLPM0                  ; [4] (72)
    lda pal_bottom_p1           ; [4] (76) Color P1 (green)
    sta COLPM1                  ; [4] (80)
    lda pal_bottom_p2           ; [4] (84) Color P2 (yellow)
    sta COLPM2                  ; [4] (88)

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
    sta HPOSP1
    sta HPOSP2
    sta ATRACT                  ; Reset OS Attract Mode timer (prevent color shift)
    lda pal_action_dragon
    sta COLPM0
    lda pal_action_p1
    sta COLPM1
    lda pal_action_p2
    sta COLPM2

    ; Update time bar counter during VBLANK
    jsr update_time_bar

    jmp XITVBV

; ==============================================================================
; TIME BAR UPDATE ROUTINE — Executed once per VBLANK
; Counts down time across 40 bar characters (each character animates codes 83..90)
; Total sub-steps = 40 * 8 = 320 steps.
; Base character: 82 (full bar), Animation: 83..90, Cleared: 0
; ==============================================================================
update_time_bar
    lda GAME_OVER_REASON
    beq @tb_run
    rts

@tb_run

    ; Advance Bresenham accumulator by total bar steps (320 = 40 chars * 8 anim steps)
    lda time_acc_lo
    clc
    adc #<320
    sta time_acc_lo
    lda time_acc_hi
    adc #>320
    sta time_acc_hi

    ; Compare time_acc with current stage total frames
    ldx current_stage
    lda time_acc_lo
    cmp stage_frames_lo,x
    lda time_acc_hi
    sbc stage_frames_hi,x
    bcc @tb_done            ; If time_acc < stage_frames, not yet time to step

    ; time_acc >= stage_frames: subtract stage_frames
    lda time_acc_lo
    sec
    sbc stage_frames_lo,x
    sta time_acc_lo
    lda time_acc_hi
    sbc stage_frames_hi,x
    sta time_acc_hi

    ; Safety check: if COUNTER_FULL is already 0, trigger game over
    lda COUNTER_FULL
    beq @tb_time_up

    ; Sprawdzamy czy ostatni znak osiągnął 90 (koniec cyklu 8 znaków)
    lda COUNTER_EIGHT
    cmp #90
    beq @tb_cycle_done

    ; Zwiększamy znak animacji o 1 (83 -> 84 -> ... -> 90)
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
    ; W momencie gdy ostatni znak na barze jest czyszczony:
    ; 1. Czyścimy ostatni znak na barze (pozycja COUNTER_FULL - 1)
    sec
    lda COUNTER_FULL
    sbc #1
    tax
    lda #0                  ; Pusta spacja (wyczyszczenie znaku)
    sta GAME_STATUS_VRAM,x

    ; 2. COUNTER_FULL jest zmniejszany o 1
    dec COUNTER_FULL
    beq @tb_time_up         ; Jeśli 0, cały pasek wyczerpany -> koniec gry!

    ; 3. Znak 83 jest kopiowany na koniec baru (nowa pozycja COUNTER_FULL - 1)
    lda #83
    sta COUNTER_EIGHT
    sec
    lda COUNTER_FULL
    sbc #1
    tax                     ; X = nowy koniec baru
    lda #83
    sta GAME_STATUS_VRAM,x  ; Kopiowanie znaku 83 na koniec baru
    rts

@tb_time_up
    lda #REASON_TIME_UP
    sta GAME_OVER_REASON

@tb_done
    rts

; ==============================================================================
; calc_stage_frames
; Calculates 16-bit total frame count (stage_frames_lo/hi) for all 3 stages:
; total_frames = (minutes * frames_per_min) + (seconds * frames_per_sec)
; Calibrated dynamically for PAL (50Hz) or NTSC (60Hz).
; ==============================================================================
calc_stage_frames
    lda PAL
    and #$08
    bne @is_ntsc
    ; PAL (50Hz: 3000 frames/min, 50 frames/sec)
    lda #<3000
    sta calc_fps_min_lo
    lda #>3000
    sta calc_fps_min_hi
    lda #50
    sta calc_fps_sec
    jmp @setup_done

@is_ntsc
    ; NTSC (60Hz: 3600 frames/min, 60 frames/sec)
    lda #<3600
    sta calc_fps_min_lo
    lda #>3600
    sta calc_fps_min_hi
    lda #60
    sta calc_fps_sec

@setup_done
    ldx #0
@stage_loop
    txa
    asl
    tay                     ; Y = stage index * 2 (offset in stage_times)

    ; Initialize frame count to 0
    lda #0
    sta stage_frames_lo,x
    sta stage_frames_hi,x

    ; Add minutes * fps_min
    lda stage_times,y       ; Stage minutes
    beq @min_done
    sta calc_temp
@min_loop
    clc
    lda stage_frames_lo,x
    adc calc_fps_min_lo
    sta stage_frames_lo,x
    lda stage_frames_hi,x
    adc calc_fps_min_hi
    sta stage_frames_hi,x
    dec calc_temp
    bne @min_loop
@min_done

    ; Add seconds * fps_sec
    lda stage_times+1,y     ; Stage seconds
    beq @sec_done
    sta calc_temp
@sec_loop
    clc
    lda stage_frames_lo,x
    adc calc_fps_sec
    sta stage_frames_lo,x
    lda stage_frames_hi,x
    adc #0
    sta stage_frames_hi,x
    dec calc_temp
    bne @sec_loop
@sec_done

    ; Safety: ensure stage has at least 320 frames
    lda stage_frames_lo,x
    ora stage_frames_hi,x
    bne @next_stage
    lda #<320
    sta stage_frames_lo,x
    lda #>320
    sta stage_frames_hi,x

@next_stage
    inx
    cpx #3
    bne @stage_loop
    rts

calc_fps_min_lo     dta 0
calc_fps_min_hi     dta 0
calc_fps_sec        dta 0
calc_temp           dta 0

; ==============================================================================
; PALETTE CONFIGURATION CELLS (editable during development / tuning)
; All colors used across the game screen and DLI interrupts
; ==============================================================================

; --- Action Screen Palette (set in dli_game_action & game_init) ---
pal_action_dragon   dta $C6         ; COLPM0: Smok (Player 0) - domyślnie zielony (Hue $C, Lum 6)
pal_action_breath   dta $28         ; COLPF3: Zianie ogniem / pociski (5th player) - złoto-pomarańczowy
pal_action_bk       dta $00         ; COLBK:  Tło ekranu akcji i ramka - czarny
pal_action_pf0      dta $00         ; COLPF0: Pole gry 0 (np. przeszkody/ziemia) - czarny
pal_action_pf1      dta $0E         ; COLPF1: Pole gry 1 (jasne elementy/tekst) - biały
pal_action_pf2      dta $00         ; COLPF2: Pole gry 2 - czarny
pal_action_p1       dta $36         ; COLPM1: Gracz 1 (np. pociski wroga) - czerwony
pal_action_p2       dta $28         ; COLPM2: Gracz 2 - złoty
pal_action_p3       dta $1A         ; COLPM3: Gracz 3 - jasnożółty

; --- Top Status Bar Palette (dli_game_top, normal text) ---
pal_top_bar         dta $02, $04, $06, $08, $08, $06, $04, $02 ; COLPF1: Pasek czasu (color bar gradient 8 scanlines)
pal_top_text        dta $0A         ; COLPF1: Domyślny kolor tekstu (legacy)
pal_top_bk          dta $70         ; COLPF2: Tło górnej linii - niebieski

; --- Bottom Status Bar Palette (dli_game_bottom, normal text) ---
pal_bottom_bar      dta $06, $08, $0a, $0c, $0c, $0a, $08, $06 ; COLPF1: Dolny pasek (color bar gradient 8 scanlines)
pal_bottom_text     dta $0A         ; COLPF1: Domyślny kolor tekstu (legacy)
pal_bottom_bk       dta $30         ; COLPF2: Tło dolnej linii - fioletowy

; --- Bottom Status Bar Sprite Overlay Configuration ---
bot_bar_p0_x        dta BOTTOM_BAR_P0_X ; Pozycja X Sprite 0 (48: lewa krawędź)
bot_bar_p1_x        dta 100             ; Pozycja X Sprite 1 (100: wycentrowany, "SCORE:")
bot_bar_p2_x        dta 168             ; Pozycja X Sprite 2 (168: prawa strona, "LIVES:")
bot_bar_pmg_y       dta 218             ; Pozycja pionowa Y paska PMG (indeks linii 0..255 w buforze)
pal_bottom_p0       dta $A0             ; Kolor Sprite 0 (cyan)
pal_bottom_p1       dta $90             ; Kolor Sprite 1 (blue-cyan)
pal_bottom_p2       dta $10             ; Kolor Sprite 2 (żółty)

; --- Time Bar & Game Over State ---
COUNTER_FULL        dta 40          ; Remaining characters on the bar (40..0)
COUNTER_EIGHT       dta 83          ; Current animation character code at end of bar (strictly 83..90)
GAME_OVER_REASON    dta 0           ; Reason game ended
current_stage       dta 0           ; Current game stage (0..2)
time_acc_lo         dta 0           ; 16-bit Bresenham time accumulator low
time_acc_hi         dta 0           ; 16-bit Bresenham time accumulator high

; --- Game Status & Score Variables ---
LEVEL               dta 1           ; Current level (1 byte, 1..255)
LIVES               dta 3           ; Remaining lives (1 byte, 0..255)
SCORE               dta 0, 0, 0, 0, 0, 0 ; Score: 6 decimal digits (each 0..9)

; --- Stage Duration Configuration (editable during development) ---
; 2 dedicated memory cells per stage (minutes, seconds)
stage_times
stage1_min          dta 1           ; Stage 1: minutes
stage1_sec          dta 20          ; Stage 1: seconds

stage2_min          dta 1           ; Stage 2: minutes
stage2_sec          dta 0           ; Stage 2: seconds

stage3_min          dta 1           ; Stage 3: minutes
stage3_sec          dta 0           ; Stage 3: seconds

; Stage frame duration tables (computed at runtime by calc_stage_frames)
stage_frames_lo     dta <3000, <3000, <3000
stage_frames_hi     dta >3000, >3000, >3000

; Game Over Reason Constants
REASON_NONE         = 0
REASON_TIME_UP      = 1             ; Czas się skończył
REASON_LIVES_OUT    = 2             ; Skończyły się życia
REASON_PLAYER_QUIT  = 3             ; Gracz zakończył grę (START)

status_line_lo
    dta <GAME_STATUS_VRAM, <(GAME_STATUS_VRAM + 40)

; --- Dragon State Variables ---
dragon_x            dta DRAGON_START_X
dragon_y            dta DRAGON_START_Y
dragon_prev_y       dta DRAGON_START_Y
dragon_sub_y        dta 0
dragon_vel_lo       dta 0
dragon_vel_hi       dta 0

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
    dta 40, d' LEVEL: 1     SCORE: 000000    LIVES: 3 '
