; ==============================================================================
; ENGINE/LEVEL_NAME.ASM — Centered Labyrinth Name Screen (ANTIC Mode 2)
; Target: Atari 800XL / 65XE (MOS 6502, MADS syntax)
; Placed in High RAM ($7800+) to preserve CODE segment headroom.
;
; Displays the labyrinth name (from world/project.yaml) centered horizontally
; on a single ANTIC Mode 2 text line, centered vertically on screen.
; Features:
;   - Fade in (luminance $00 -> $0E)
;   - Hold at peak brightness
;   - Fade out (luminance $0E -> $00)
;   - Fast-forward / skip on joystick FIRE trigger
;   - Seamless transition to action flight screen
; ==============================================================================

LEVEL_NAME_FADE_SPEED   = 5     ; Frames per luminance step (7 steps * 5 = 35 frames fade in)
LEVEL_NAME_HOLD_FRAMES  = 4     ; Hold steps at peak luminance (4 steps * 5 = 20 frames = 0.4s)
LEVEL_NAME_FAST_SPEED   = 1     ; Fast-forward speed when FIRE is pressed

LEVEL_NAME_STATE_IN     = 0     ; Fading in
LEVEL_NAME_STATE_HOLD   = 1     ; Holding at peak
LEVEL_NAME_STATE_OUT    = 2     ; Fading out
LEVEL_NAME_STATE_DONE   = 3     ; Finished

; --- State Storage ---
level_name_state        dta 0
level_name_timer        dta 0
level_name_lum          dta 0
level_name_hold_timer   dta 0
level_name_speed        dta 0

; ==============================================================================
; show_level_name_screen
; Configures ANTIC for 1-line centered Mode 2 screen, prints centered name in STUB_VRAM,
; resets luminance to black, and sets game_substate = SUBSTATE_LEVEL_NAME.
; ==============================================================================
.proc show_level_name_screen
    ; 1. Disable DMA, PMG, and DLIs while reconfiguring display
    lda #0
    sta SDMCTL
    sta DMACTL
    sta NMIEN                   ; Disable interrupts (no DLI, no VBL)
    jsr disable_pmg

    ; 2. Use default text font ($7000)
    lda #>FONT_ADDR
    sta CHBASE
    sta CHBAS

    ; 3. Clear 40 bytes of STUB_VRAM (single line) with space ($00)
    lda #0
    ldx #39
@clr_stub
    sta STUB_VRAM,x
    dex
    bpl @clr_stub

    ; 4. Fetch current level name pointer from compiled world data
    ldx current_level_idx
    cpx #WORLD_LABYRINTHS_COUNT
    bcc @valid_lab
    ldx #0
@valid_lab
    lda labyrinths_name_lo,x
    sta PTR_SRC
    lda labyrinths_name_hi,x
    sta PTR_SRC+1

    ; Read string length
    ldy #0
    lda (PTR_SRC),y
    beq @copy_done
    sta ZP_TMP                  ; ZP_TMP = string length

    ; Calculate centered horizontal column: col = (40 - len) / 2
    lda #40
    sec
    sbc ZP_TMP
    lsr
    tax                         ; X = destination column in STUB_VRAM

    ; Copy display codes to STUB_VRAM,x
    ldy #1
@copy_loop
    lda (PTR_SRC),y
    sta STUB_VRAM,x
    inx
    iny
    cpy ZP_TMP
    bcc @copy_loop
    beq @copy_loop

@copy_done
    ; 5. Set DLIST pointer to dlist_level_name
    lda #<dlist_level_name
    sta SDLSTL
    sta DLISTL
    lda #>dlist_level_name
    sta SDLSTH
    sta DLISTH

    ; 6. Set black background and initial black text
    lda #$00
    sta COLOR2
    sta COLPF2                  ; Text background = black
    sta COLOR4
    sta COLBK                   ; Border / screen background = black
    sta COLOR1
    sta COLPF1                  ; Text luminance = black ($00)

    ; 7. Reset fade state
    sta level_name_lum
    sta level_name_state        ; LEVEL_NAME_STATE_IN = 0
    lda #LEVEL_NAME_FADE_SPEED
    sta level_name_speed
    sta level_name_timer
    lda #LEVEL_NAME_HOLD_FRAMES
    sta level_name_hold_timer

    ; 8. Enable normal playfield DMA (%00100010 = $22)
    lda #$22
    sta SDMCTL
    sta DMACTL

    ; Enable VBLANK only ($40), no DLI
    lda #$40
    sta NMIEN

    ; 9. Switch game substate to level name screen
    lda #SUBSTATE_LEVEL_NAME
    sta game_substate
    rts
.endp

; ==============================================================================
; update_level_name_screen
; Drives the fade-in, hold, and fade-out animation once per frame.
; Checks joystick trigger (STRIG0 / fire_pressed) to accelerate/skip.
; ==============================================================================
.proc update_level_name_screen
    ; 1. Check if user pressed FIRE on joystick to fast-forward / skip
    lda STRIG0
    beq @fire_hit
    lda fire_pressed
    beq @no_fire

@fire_hit
    ; If in fade in or hold, accelerate to fast fade out
    lda level_name_state
    cmp #LEVEL_NAME_STATE_OUT
    bcs @already_fading_out
    lda #LEVEL_NAME_STATE_OUT
    sta level_name_state
    lda #LEVEL_NAME_FAST_SPEED
    sta level_name_speed
    sta level_name_timer
    bne @step_timer

@already_fading_out
    ; Accelerate fade out to 1 frame per step
    lda #LEVEL_NAME_FAST_SPEED
    sta level_name_speed

@no_fire
@step_timer
    dec level_name_timer
    bne @apply_color
    lda level_name_speed
    sta level_name_timer

    ; Check current phase
    lda level_name_state
    bne @check_hold

    ; --- Phase 0: FADE IN ($00 -> $0E) ---
    lda level_name_lum
    clc
    adc #2
    sta level_name_lum
    cmp #$0E
    bcc @apply_color
    ; Reached maximum luminance ($0E), transition to HOLD
    lda #$0E
    sta level_name_lum
    lda #LEVEL_NAME_STATE_HOLD
    sta level_name_state
    jmp @apply_color

@check_hold
    cmp #LEVEL_NAME_STATE_HOLD
    bne @check_fade_out

    ; --- Phase 1: HOLD ---
    dec level_name_hold_timer
    bne @apply_color
    ; Hold complete, transition to FADE OUT
    lda #LEVEL_NAME_STATE_OUT
    sta level_name_state
    jmp @apply_color

@check_fade_out
    cmp #LEVEL_NAME_STATE_OUT
    bne @check_done

    ; --- Phase 2: FADE OUT ($0E -> $00) ---
    lda level_name_lum
    beq @fade_out_finished
    sec
    sbc #2
    sta level_name_lum
    jmp @apply_color

@fade_out_finished
    lda #LEVEL_NAME_STATE_DONE
    sta level_name_state

@check_done
    ; Phase 3: DONE -> start action flight screen!
    jsr start_action_flight
    rts

@apply_color
    lda level_name_lum
    sta COLOR1
    sta COLPF1
    rts
.endp

; ==============================================================================
; start_action_flight
; Reconfigures ANTIC & GTIA for the action flight screen (dlist_game),
; restores playfield colors, sets up DLIs and VBLANK, and enables PMG.
; ==============================================================================
.proc start_action_flight
    ; Blank DMA during reconfiguration
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Set DLIST pointer to main game display list
    lda #<dlist_game
    sta SDLSTL
    sta DLISTL
    lda #>dlist_game
    sta SDLSTH
    sta DLISTH

    ; Restore action screen colors from compiled world/colors.yaml
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

    ; Set player/missile colors
    lda pal_action_dragon
    sta PCOLR0
    sta COLPM0
    lda pal_action_p1
    sta PCOLR1
    sta COLPM1
    lda pal_action_p2
    sta PCOLR2
    sta COLPM2
    lda pal_action_p3
    sta PCOLR3
    sta COLPM3

    ; Set PMBASE (page $20 = $2000)
    lda #>PM_ADDR
    sta PMBASE

    ; Configure Player 0 hardware (Dragon)
    lda #DRAGON_START_X
    sta dragon_x
    sta HPOSP0
    lda #0
    sta SIZEP0

    ; Priority: Player 0 in front of playfield + 5th player mode for missiles ($09)
    lda #$09
    sta GPRIOR
    sta PRIOR

    ; Enable player and missile display in GTIA (bit 0=missiles, bit 1=players)
    lda #3
    sta GRACTL
    sta HITCLR

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

    ; Re-render dragon sprite into Player 0 buffer
    jsr render_dragon

    ; Enable playfield DMA + single-line PMG + Player DMA + Missile DMA (%00111110 = $3E)
    lda #$3E
    sta SDMCTL
    sta DMACTL

    ; Enable NMI: VBLANK ($40) + DLI ($80) = $C0
    lda #$C0
    sta NMIEN

    ; Switch game substate to active gameplay
    lda #SUBSTATE_PLAYING
    sta game_substate
    rts
.endp
