; ==============================================================================
; SCENES/GAME.ASM — Main Gameplay Scene
; Target: 11 lines ANTIC Mode 5 (Action) + 2 lines ANTIC Mode 2 (Status)
; Sprite: Animated Jabberwocky dragon (Player 0) with 16-bit Phase Accumulator
; ==============================================================================

; --- Dragon Configuration Constants ---
DRAGON_START_X          = 64            ; Left side of action playfield
DRAGON_START_Y          = 99            ; Centered vertically in ANTIC 5 (24..199, H=26)
DRAGON_MIN_Y            = 24            ; Top boundary (first scanline of ANTIC 5)
DRAGON_MAX_Y            = 173           ; Bottom boundary (199 - 26 = 173, above status)
DRAGON_COLOR            = $C6           ; Dragon green (Hue $C, Lum 6)

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
SCROLL_MAX_SPEED        = $0400         ; Max horizontal scroll velocity (4.0 px/frame)
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

    ; Clear Player 0 buffer ($2400-$24FF)
    tax
@   sta P0_ADDR,x
    inx
    bne @-

    ; Set PMBASE (page $20 = $2000)
    lda #>PM_ADDR
    sta PMBASE

    ; Configure Player 0 hardware
    lda #DRAGON_START_X
    sta HPOSP0
    lda #0
    sta SIZEP0              ; Normal width (8 color clocks)
    lda #DRAGON_COLOR
    sta PCOLR0
    sta COLPM0

    ; Priority: Player 0 in front of playfield
    lda #$01
    sta GPRIOR
    sta PRIOR

    ; Enable player display in GTIA
    lda #2
    sta GRACTL
    sta HITCLR

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
    lda #$FF
    sta last_status_tier

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

    ; Set Colors:
    ; Action screen background & border: Black ($00)
    ; Status screen (Mode 2): Black background ($00), White text ($0E)
    lda #$00
    sta COLOR0
    sta COLPF0
    sta COLOR2
    sta COLPF2
    sta COLOR3
    sta COLPF3
    sta COLOR4
    sta COLBK

    lda #$0E
    sta COLOR1
    sta COLPF1

    ; Clear 440 bytes of action playfield ($6000-$61B7) with empty tiles (0)
    lda #0
    ldx #0
@   sta GAME_ACTION_VRAM,x
    cpx #440-256        ; 184 ($B8)
    bcs @+
    sta GAME_ACTION_VRAM+256,x
@   inx
    bne @-1

    ; Clear 80 bytes of status bar ($6200-$624F) with 0 (space)
    lda #0
    ldx #79
@   sta GAME_STATUS_VRAM,x
    dex
    bpl @-

    ; Print status bar title (row 0)
    lda #<status_txt_row0
    sta PTR_SRC
    lda #>status_txt_row0
    sta PTR_SRC+1
    ldx #0
    jsr print_status_line

    ; Print initial status bar speed (row 1)
    jsr update_status_speed_display

    ; Initial render of dragon sprite into Player 0 buffer
    jsr render_dragon

    ; Enable playfield DMA + single-line PMG + Player DMA (%00111010 = $3A)
    lda #$3A
    sta SDMCTL
    sta DMACTL
    rts

game_run
    ; 1. Check FIRE button to exit to Game Over
    lda fire_pressed
    beq @not_fire
    lda #0
    sta fire_pressed
    jsr disable_pmg
    lda #STATE_GAME_OVER
    sta game_state
    rts

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

    ; Clamp to SCROLL_MAX_SPEED ($0400 = 4.0 px/frame)
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

    ; Update status bar display if speed tier changed
    jsr update_status_speed_display

    ; 5. Commit/render sprite to Player 0 buffer (during VBLANK phase)
    jsr render_dragon
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
    rts

; ==============================================================================
; UPDATE STATUS BAR SPEED DISPLAY
; Maps SCROLL_SPEED to 5 informative status tiers (0..4) and redraws row 1
; ==============================================================================
update_status_speed_display
    ; Determine speed tier (0 = Hover, 1..3 = Cruise, 4 = Max)
    lda SCROLL_SPEED+1
    bne @chk_high_tiers
    lda SCROLL_SPEED
    beq @tier_0
    cmp #$80
    bcc @tier_1
    jmp @tier_2

@chk_high_tiers
    cmp #$02
    bcc @tier_2
    beq @tier_3
    jmp @tier_4

@tier_0
    ldx #0
    jmp @draw_tier
@tier_1
    ldx #1
    jmp @draw_tier
@tier_2
    ldx #2
    jmp @draw_tier
@tier_3
    ldx #3
    jmp @draw_tier
@tier_4
    ldx #4

@draw_tier
    cpx last_status_tier
    beq @tier_done                  ; Already displaying this tier, skip redraw
    stx last_status_tier

    lda status_speed_tbl_lo,x
    sta PTR_SRC
    lda status_speed_tbl_hi,x
    sta PTR_SRC+1
    ldx #1
    jsr print_status_line

@tier_done
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
    beq @done
    tax                 ; X = length counter

    ldy #1
@   lda (PTR_SRC),y
    dey
    sta (PTR_DST),y
    iny
    iny
    dex
    bne @-

@done
    rts

status_line_lo
    dta <GAME_STATUS_VRAM, <(GAME_STATUS_VRAM + 40)

; --- Dragon Vertical State Variables ---
dragon_y            dta DRAGON_START_Y
dragon_prev_y       dta DRAGON_START_Y
dragon_sub_y        dta 0
dragon_vel_lo       dta 0
dragon_vel_hi       dta 0

; --- 16-bit Animation & Scroll Variables ---
ANIM_PHASE          dta a(0)        ; 16-bit Phase Accumulator: low=fraction, high=frame (0..5)
ANIM_SPEED          dta a(BASE_HOVER_SPEED) ; 16-bit Animation rate: BASE_HOVER_SPEED + (SCROLL_SPEED / 4)
SCROLL_SPEED        dta a(0)        ; 16-bit Horizontal scroll speed (8.8 fixed-point)
last_status_tier    dta $FF         ; Cached tier (0..4) to avoid redrawing status every frame

; --- Status Bar Speed Text Pointers (SoA) ---
status_speed_tbl_lo
    dta <speed_txt_0, <speed_txt_1, <speed_txt_2, <speed_txt_3, <speed_txt_4
status_speed_tbl_hi
    dta >speed_txt_0, >speed_txt_1, >speed_txt_2, >speed_txt_3, >speed_txt_4

; --- Status Bar Text Data (ANTIC display codes) ---
status_txt_row0
    dta 40, d' JABBERWOCKY - GAMEPLAY ARENA (ANTIC 5) '

speed_txt_0
    dta 40, d' SPEED: HOVER (BASE)     >> FIRE: EXIT <<'
speed_txt_1
    dta 40, d' SPEED: CRUISE 1         >> FIRE: EXIT <<'
speed_txt_2
    dta 40, d' SPEED: CRUISE 2         >> FIRE: EXIT <<'
speed_txt_3
    dta 40, d' SPEED: CRUISE 3         >> FIRE: EXIT <<'
speed_txt_4
    dta 40, d' SPEED: FULL FLAP (MAX)  >> FIRE: EXIT <<'
