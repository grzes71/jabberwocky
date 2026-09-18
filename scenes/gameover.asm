; ==============================================================================
; SCENES/GAMEOVER.ASM — Game Over Scene Stub (ANTIC Mode 2 / Gr.0)
; ==============================================================================

gameover_init
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

    ; Set DLIST pointer to stub text display list
    lda #<dlist_stub
    sta SDLSTL
    sta DLISTL
    lda #>dlist_stub
    sta SDLSTH
    sta DLISTH

    ; Check if VICTORY / SUCCESS
    lda GAME_OVER_REASON
    cmp #REASON_SUCCESS
    beq @init_victory

    ; Colors: Deep red background ($32) and border ($32) with white text ($0E)
    lda #$32
    sta COLOR2
    sta COLPF2
    sta COLOR4
    sta COLBK

    lda #$0E
    sta COLOR1
    sta COLPF1

    ; Clear text screen
    jsr clear_stub_vram

    ; Print game over text
    lda #<gover_txt_title
    sta PTR_SRC
    lda #>gover_txt_title
    sta PTR_SRC+1
    ldx #3
    ldy #11
    jsr print_at

    lda #<gover_txt_line1
    sta PTR_SRC
    lda #>gover_txt_line1
    sta PTR_SRC+1
    ldx #8
    jsr print_centered_line

    lda #<gover_txt_line2
    sta PTR_SRC
    lda #>gover_txt_line2
    sta PTR_SRC+1
    ldx #10
    jsr print_centered_line

    lda #<gover_txt_line3
    sta PTR_SRC
    lda #>gover_txt_line3
    sta PTR_SRC+1
    ldx #12
    jsr print_centered_line

    lda #<gover_txt_line4
    sta PTR_SRC
    lda #>gover_txt_line4
    sta PTR_SRC+1
    ldx #14
    jsr print_centered_line
    jmp @gover_common_prompt

@init_victory
    ; Colors: Deep green background ($C4) and border ($C4) with golden/white text ($1E)
    lda #$C4
    sta COLOR2
    sta COLPF2
    sta COLOR4
    sta COLBK

    lda #$1E
    sta COLOR1
    sta COLPF1

    ; Clear text screen
    jsr clear_stub_vram

    ; Print victory text
    lda #<win_txt_title
    sta PTR_SRC
    lda #>win_txt_title
    sta PTR_SRC+1
    ldx #3
    ldy #12
    jsr print_at

    lda #<win_txt_line1
    sta PTR_SRC
    lda #>win_txt_line1
    sta PTR_SRC+1
    ldx #8
    jsr print_centered_line

    lda #<win_txt_line2
    sta PTR_SRC
    lda #>win_txt_line2
    sta PTR_SRC+1
    ldx #10
    jsr print_centered_line

    lda #<win_txt_line3
    sta PTR_SRC
    lda #>win_txt_line3
    sta PTR_SRC+1
    ldx #12
    jsr print_centered_line

    lda #<win_txt_line4
    sta PTR_SRC
    lda #>win_txt_line4
    sta PTR_SRC+1
    ldx #14
    jsr print_centered_line

@gover_common_prompt
    lda #<gover_txt_prompt
    sta PTR_SRC
    lda #>gover_txt_prompt
    sta PTR_SRC+1
    ldx #20
    ldy #6
    jsr print_at

    ; Enable playfield DMA ($22)
    lda #$22
    sta SDMCTL
    sta DMACTL
    rts

; Print string pointed by PTR_SRC horizontally centered at row X
print_centered_line
    ldy #0
    lda (PTR_SRC),y
    beq @+                      ; If length == 0, skip
    sec
    lda #40
    ldy #0
    sbc (PTR_SRC),y
    lsr
    tay                         ; Y = (40 - len) / 2
    jsr print_at
@   rts

gameover_run
    lda fire_pressed
    beq @+
    lda #0
    sta fire_pressed
    lda #STATE_TOP_SCORES
    sta game_state
@   rts

; --- Text Data ---
gover_txt_title
    dta 17, d'=== GAME OVER ==='

win_txt_title
    dta 15, d'=== VICTORY ==='

gover_txt_prompt
    dta 26, d'>> PRESS FIRE TO RESTART <<'*

; --- Auto-generated Game Over texts from texts/ ---
    icl 'gen/game_over_fail_text.asm'
    icl 'gen/game_over_success_text.asm'
