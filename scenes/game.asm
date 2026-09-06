; ==============================================================================
; SCENES/GAME.ASM — Main Game Scene Stub (ANTIC Mode 2 / Gr.0)
; ==============================================================================

game_init
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

    ; Colors: Deep forest green background with white text
    lda #$C2
    sta COLOR2
    sta COLPF2

    lda #$0E
    sta COLOR1
    sta COLPF1

    lda #$C0
    sta COLOR4
    sta COLBK

    ; Clear text screen
    jsr clear_stub_vram

    ; Print game arena stub text
    lda #<game_txt_title
    sta PTR_SRC
    lda #>game_txt_title
    sta PTR_SRC+1
    ldx #2
    ldy #5
    jsr print_at

    lda #<game_txt_arena
    sta PTR_SRC
    lda #>game_txt_arena
    sta PTR_SRC+1
    ldx #7
    ldy #8
    jsr print_at

    lda #<game_txt_desc1
    sta PTR_SRC
    lda #>game_txt_desc1
    sta PTR_SRC+1
    ldx #10
    ldy #4
    jsr print_at

    lda #<game_txt_desc2
    sta PTR_SRC
    lda #>game_txt_desc2
    sta PTR_SRC+1
    ldx #12
    ldy #6
    jsr print_at

    lda #<game_txt_prompt
    sta PTR_SRC
    lda #>game_txt_prompt
    sta PTR_SRC+1
    ldx #20
    ldy #5
    jsr print_at

    ; Enable playfield DMA ($22)
    lda #$22
    sta SDMCTL
    sta DMACTL
    rts

game_run
    lda fire_pressed
    beq @+
    lda #0
    sta fire_pressed
    lda #STATE_GAME_OVER
    sta game_state
@   rts

; --- Text Data ---
game_txt_title
    dta 30, d'=== JABBERWOCKY: MAIN GAME ==='
game_txt_arena
    dta 24, d'[ GAMEPLAY ARENA - STUB ]'
game_txt_desc1
    dta 32, d'THE HERO EXPLORES TULGEY WOOD...'
game_txt_desc2
    dta 27, d'AND RESTED BY THE TUMTUM TREE'
game_txt_prompt
    dta 29, d'>> PRESS FIRE FOR GAME OVER <<'*
