; ==============================================================================
; SCENES/INTRO.ASM — Introduction Screen with Bidirectional DLI Fade Effect
; Target: ANTIC Mode 2 (40x24) + DLI luminance per text line
; Fade in: line 0 -> 1 -> 2 -> 3 (top to bottom)
; Fade out on FIRE: line 3 -> 2 -> 1 -> 0 (bottom to top), then transition to game
; ==============================================================================

FADE_IN_DELAY   = 6         ; Frame delay between luminance increments (fade in)
FADE_OUT_DELAY  = 4         ; Frame delay between luminance decrements (fade out)

FADE_MODE_IN    = 0
FADE_MODE_WAIT  = 1
FADE_MODE_OUT   = 2
FADE_MODE_DONE  = 3

intro_init
    ; Blank DMA during reconfiguration
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset PMG
    jsr disable_pmg

    ; Use default text font ($7000)
    lda #>FONT_ADDR
    sta CHBASE
    sta CHBAS

    ; Set DLIST pointer to intro display list (with DLIs)
    lda #<dlist_intro
    sta SDLSTL
    sta DLISTL
    lda #>dlist_intro
    sta SDLSTH
    sta DLISTH

    ; Colors: Black background ($00) and initial black text ($00)
    lda #$00
    sta COLOR2
    sta COLPF2
    sta COLOR4
    sta COLBK
    sta COLOR1                  ; Shadow text color = black
    sta COLPF1                  ; Hardware text color = black

    ; Reset 4 line color cells (start black) & fade state
    sta intro_line_col0
    sta intro_line_col1
    sta intro_line_col2
    sta intro_line_col3
    sta intro_fade_line
    sta intro_fade_mode         ; FADE_MODE_IN = 0
    lda #FADE_IN_DELAY
    sta intro_fade_timer

    ; Set initial DLI vector (points to line 1 handler)
    lda #<dli_intro_line1
    sta VDSLST
    lda #>dli_intro_line1
    sta VDSLST+1

    ; Install Deferred VBLANK vector via OS SETVBV
    ldy #<vblank_intro
    ldx #>vblank_intro
    lda #7                      ; Type 7 = Deferred VBLANK
    jsr SETVBV

    ; Clear text screen
    jsr clear_stub_vram

    ; Print intro poem lines (centered vertically and horizontally)
    lda #<intro_txt_line1
    sta PTR_SRC
    lda #>intro_txt_line1
    sta PTR_SRC+1
    ldx #9
    ldy #3
    jsr print_at

    lda #<intro_txt_line2
    sta PTR_SRC
    lda #>intro_txt_line2
    sta PTR_SRC+1
    ldx #11
    ldy #3
    jsr print_at

    lda #<intro_txt_line3
    sta PTR_SRC
    lda #>intro_txt_line3
    sta PTR_SRC+1
    ldx #13
    ldy #5
    jsr print_at

    lda #<intro_txt_line4
    sta PTR_SRC
    lda #>intro_txt_line4
    sta PTR_SRC+1
    ldx #15
    ldy #6
    jsr print_at

    ; Enable playfield DMA (standard width, no PMG: $22)
    lda #$22
    sta SDMCTL
    sta DMACTL

    ; Enable NMI: VBLANK ($40) + DLI ($80) = $C0
    lda #$C0
    sta NMIEN
    rts

intro_run
    ; Check if fade out is complete -> transition to game
    lda intro_fade_mode
    cmp #FADE_MODE_DONE
    beq @transition_game

    ; Check if player pressed FIRE button
    lda fire_pressed
    beq @run_done

    lda #0
    sta fire_pressed

    ; If already fading out or done, do nothing
    lda intro_fade_mode
    cmp #FADE_MODE_OUT
    beq @run_done
    cmp #FADE_MODE_DONE
    beq @run_done

    ; Initiate fade-out from bottom line (3) to top line (0)
    lda #FADE_MODE_OUT
    sta intro_fade_mode
    lda #3
    sta intro_fade_line
    lda #FADE_OUT_DELAY
    sta intro_fade_timer
    rts

@transition_game
    ; Disable DLI before leaving scene
    lda #$40                    ; VBLANK only, DLI disabled
    sta NMIEN

    ; Restore default deferred VBLANK vector
    ldy #<XITVBV
    ldx #>XITVBV
    lda #7                      ; Deferred VBLANK
    jsr SETVBV

    lda #0
    sta fire_pressed
    lda #STATE_GAME
    sta game_state

@run_done
    rts

; ==============================================================================
; DLI ROUTINES — Triggered before each of the 4 text lines
; Each DLI writes the current line's color cell to hardware register COLPF1 ($D017)
; and chains VDSLST to the next line's handler.
; ==============================================================================

dli_intro_line1
    pha                         ; [3] (3) Save accumulator
    lda intro_line_col0         ; [4] (7) Fetch line 1 color cell
    sta WSYNC                   ; [4] (11) Wait for horizontal sync
    sta COLPF1                  ; [4] (4) Hardware register $D017 (NOT shadow!)
    lda #<dli_intro_line2       ; [2] (6) Next DLI vector low
    sta VDSLST                  ; [4] (10)
    lda #>dli_intro_line2       ; [2] (12) Next DLI vector high
    sta VDSLST+1                ; [4] (16)
    pla                         ; [4] (20) Restore accumulator
    rti                         ; [6] (26) Return from interrupt

dli_intro_line2
    pha                         ; [3] (3) Save accumulator
    lda intro_line_col1         ; [4] (7) Fetch line 2 color cell
    sta WSYNC                   ; [4] (11) Wait for horizontal sync
    sta COLPF1                  ; [4] (4) Hardware register $D017
    lda #<dli_intro_line3       ; [2] (6) Next DLI vector low
    sta VDSLST                  ; [4] (10)
    lda #>dli_intro_line3       ; [2] (12) Next DLI vector high
    sta VDSLST+1                ; [4] (16)
    pla                         ; [4] (20) Restore accumulator
    rti                         ; [6] (26) Return from interrupt

dli_intro_line3
    pha                         ; [3] (3) Save accumulator
    lda intro_line_col2         ; [4] (7) Fetch line 3 color cell
    sta WSYNC                   ; [4] (11) Wait for horizontal sync
    sta COLPF1                  ; [4] (4) Hardware register $D017
    lda #<dli_intro_line4       ; [2] (6) Next DLI vector low
    sta VDSLST                  ; [4] (10)
    lda #>dli_intro_line4       ; [2] (12) Next DLI vector high
    sta VDSLST+1                ; [4] (16)
    pla                         ; [4] (20) Restore accumulator
    rti                         ; [6] (26) Return from interrupt

dli_intro_line4
    pha                         ; [3] (3) Save accumulator
    lda intro_line_col3         ; [4] (7) Fetch line 4 color cell
    sta WSYNC                   ; [4] (11) Wait for horizontal sync
    sta COLPF1                  ; [4] (4) Hardware register $D017
    lda #<dli_intro_line1       ; [2] (6) Reset DLI vector back to line 1
    sta VDSLST                  ; [4] (10)
    lda #>dli_intro_line1       ; [2] (12)
    sta VDSLST+1                ; [4] (16)
    pla                         ; [4] (20) Restore accumulator
    rti                         ; [6] (26) Return from interrupt

; ==============================================================================
; VBLANK ROUTINE — Runs during deferred vertical blank (Type 7)
; Resets initial DLI vector and drives the gradual line-by-line fade in/out
; ==============================================================================
vblank_intro
    ; Ensure DLI vector is set to line 1 for the upcoming frame
    lda #<dli_intro_line1
    sta VDSLST
    lda #>dli_intro_line1
    sta VDSLST+1

    ; Update text fading
    jsr update_intro_fade

    jmp XITVBV

; Drives fade in (lines 0..3 up to $0E) and fade out (lines 3..0 down to $00)
update_intro_fade
    lda intro_fade_mode
    bne @check_fade_out

    ; --- FADE IN: Lines 0 -> 1 -> 2 -> 3 ---
    dec intro_fade_timer
    bne @fade_ret

    lda #FADE_IN_DELAY
    sta intro_fade_timer

    ldx intro_fade_line
    lda intro_line_col0,x
    clc
    adc #$02
    sta intro_line_col0,x
    cmp #$0E
    bcc @fade_ret

    ; Line X reached $0E -> advance to next line
    inc intro_fade_line
    lda intro_fade_line
    cmp #4
    bcc @fade_ret

    ; All 4 lines reached $0E -> wait for fire button
    lda #FADE_MODE_WAIT
    sta intro_fade_mode
@fade_ret
    rts

@check_fade_out
    cmp #FADE_MODE_OUT
    bne @fade_ret

    ; --- FADE OUT: Lines 3 -> 2 -> 1 -> 0 ---
    dec intro_fade_timer
    bne @fade_ret

    lda #FADE_OUT_DELAY
    sta intro_fade_timer

@fade_out_step
    ldx intro_fade_line         ; 3, 2, 1, 0
    lda intro_line_col0,x
    beq @line_is_zero

    sec
    sbc #$02
    sta intro_line_col0,x
    bne @fade_ret               ; If not zero yet, continue next frame

@line_is_zero
    cpx #0
    beq @all_zeroed

    ; Move to previous line (upwards)
    dex
    stx intro_fade_line
    lda intro_line_col0,x
    beq @fade_out_step          ; If previous line is already zero, keep stepping
    rts

@all_zeroed
    lda #FADE_MODE_DONE
    sta intro_fade_mode
    rts

; --- Text Color Cells (4 lines) & Fade State ---
intro_line_col0     dta 0
intro_line_col1     dta 0
intro_line_col2     dta 0
intro_line_col3     dta 0
intro_fade_line     dta 0
intro_fade_timer    dta FADE_IN_DELAY
intro_fade_mode     dta FADE_MODE_IN

; --- Text Data (Included from generated text compiler) ---
    icl 'gen/intro_text.asm'


