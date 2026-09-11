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

    ; Colors: Deep red background with white text (Game Over / Defeat)
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
    jmp @gover_common_prompt

@init_victory
    ; Colors: Deep green background ($C4) with golden/white text ($1E)
    lda #$C4
    sta COLOR2
    sta COLPF2

    lda #$1E
    sta COLOR1
    sta COLPF1

    lda #$C0
    sta COLOR4
    sta COLBK

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
    ldy #3
    jsr print_at

    lda #<win_txt_line2
    sta PTR_SRC
    lda #>win_txt_line2
    sta PTR_SRC+1
    ldx #10
    ldy #4
    jsr print_at

    lda #<win_txt_line3
    sta PTR_SRC
    lda #>win_txt_line3
    sta PTR_SRC+1
    ldx #13
    ldy #4
    jsr print_at

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

win_txt_title
    dta 15, d'=== VICTORY ==='
win_txt_line1
    dta 34, d'AND HAST THOU SLAIN THE JABBERWOCK?'
win_txt_line2
    dta 32, d'COME TO MY ARMS, MY BEAMISH BOY!'
win_txt_line3
    dta 32, d'O FRABJOUS DAY! CALLOOH! CALLAY!'

gover_txt_prompt
    dta 26, d'>> PRESS FIRE TO RESTART <<'*
