; ==============================================================================
; SCENES/INTRO.ASM — Introduction Screen Stub (ANTIC Mode 2 / Gr.0)
; ==============================================================================

intro_init
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

    ; Colors: Deep blue background with white text
    lda #$94
    sta COLOR2
    sta COLPF2

    lda #$0E
    sta COLOR1
    sta COLPF1

    lda #$90
    sta COLOR4
    sta COLBK

    ; Clear text screen
    jsr clear_stub_vram

    ; Print intro text
    lda #<intro_txt_title
    sta PTR_SRC
    lda #>intro_txt_title
    sta PTR_SRC+1
    ldx #2
    ldy #7
    jsr print_at

    lda #<intro_txt_line1
    sta PTR_SRC
    lda #>intro_txt_line1
    sta PTR_SRC+1
    ldx #6
    ldy #5
    jsr print_at

    lda #<intro_txt_line2
    sta PTR_SRC
    lda #>intro_txt_line2
    sta PTR_SRC+1
    ldx #8
    ldy #2
    jsr print_at

    lda #<intro_txt_line3
    sta PTR_SRC
    lda #>intro_txt_line3
    sta PTR_SRC+1
    ldx #11
    ldy #4
    jsr print_at

    lda #<intro_txt_line4
    sta PTR_SRC
    lda #>intro_txt_line4
    sta PTR_SRC+1
    ldx #13
    ldy #7
    jsr print_at

    lda #<intro_txt_prompt
    sta PTR_SRC
    lda #>intro_txt_prompt
    sta PTR_SRC+1
    ldx #20
    ldy #7
    jsr print_at

    ; Enable playfield DMA (standard width, no PMG: $22)
    lda #$22
    sta SDMCTL
    sta DMACTL
    rts

intro_run
    lda fire_pressed
    beq @+
    lda #0
    sta fire_pressed
    lda #STATE_GAME
    sta game_state
@   rts

; --- Text Data (Length prefix + ANTIC display codes) ---
intro_txt_title
    dta 26, d'=== JABBERWOCKY: INTRO ==='
intro_txt_line1
    dta 30, d'BEWARE THE JABBERWOCK, MY SON!'
intro_txt_line2
    dta 36, d'THE JAWS THAT BITE, THE CLAWS CATCH!'
intro_txt_line3
    dta 32, d'BEWARE THE JUBJUB BIRD, AND SHUN'
intro_txt_line4
    dta 26, d'THE FRUMIOUS BANDERSNATCH!'
intro_txt_prompt
    dta 25, d'>> PRESS FIRE TO START <<'*
