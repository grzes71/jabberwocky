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

    ; Use OS ROM font ($E000)
    lda #$E0
    sta CHBASE

    ; Set DLIST pointer to stub text display list
    lda #<dlist_stub
    sta SDLSTL
    sta DLISTL
    lda #>dlist_stub
    sta SDLSTH
    sta DLISTH

    ; Colors: Deep red background with white text
    lda #$32
    sta COLOR2
    sta COLPF2

    lda #$0E
    sta COLOR1
    sta COLPF1

    lda #$30
    sta COLOR4
    sta COLBK

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
    ldy #3
    jsr print_at

    lda #<gover_txt_line2
    sta PTR_SRC
    lda #>gover_txt_line2
    sta PTR_SRC+1
    ldx #10
    ldy #2
    jsr print_at

    lda #<gover_txt_line3
    sta PTR_SRC
    lda #>gover_txt_line3
    sta PTR_SRC+1
    ldx #13
    ldy #2
    jsr print_at

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

gameover_run
    lda fire_pressed
    beq @+
    lda #0
    sta fire_pressed
    lda #STATE_TITLE
    sta game_state
@   rts

; --- Text Data ---
gover_txt_title
    dta 17, d'=== GAME OVER ==='
gover_txt_line1
    dta 33, d'ONE, TWO! AND THROUGH AND THROUGH'
gover_txt_line2
    dta 36, d'THE VORPAL BLADE WENT SNICKER-SNACK!'
gover_txt_line3
    dta 36, d'THE JABBERWOCK HAS CLAIMED YOUR SOUL'
gover_txt_prompt
    dta 26, d'>> PRESS FIRE TO RESTART <<'*
