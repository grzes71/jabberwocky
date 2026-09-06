; ==============================================================================
; SCENES/TITLE.ASM — Title Screen Scene
; Target: ANTIC Mode F (320x175) + 3-Player PMG
; ==============================================================================

title_init
    ; Blank screen DMA during setup
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset GTIA PMG latches
    sta GRACTL
    sta GRAFP0
    sta GRAFP1
    sta GRAFP2
    sta GRAFP3
    sta GRAFM

    ; Clear PMG memory area ($2000-$27FF, 2KB)
    tax
@   sta PM_ADDR,x
    sta PM_ADDR+$100,x
    sta PM_ADDR+$200,x
    sta PM_ADDR+$300,x
    sta PM_ADDR+$400,x
    sta PM_ADDR+$500,x
    sta PM_ADDR+$600,x
    sta PM_ADDR+$700,x
    inx
    bne @-

    ; Draw 43-line sprite pattern into Player 0, 1, and 2
    ldx #0
    lda #$FF
@   sta P0_ADDR + SPRITE_Y,x
    sta P1_ADDR + SPRITE_Y,x
    sta P2_ADDR + SPRITE_Y,x
    inx
    cpx #SPRITE_H
    bne @-

    ; Set PMBASE (page $20)
    lda #>PM_ADDR
    sta PMBASE

    ; Configure Player positions: side by side (X, X+32, X+64)
    lda #SPRITE_X
    sta HPOSP0
    lda #SPRITE_X + SPRITE_W
    sta HPOSP1
    lda #SPRITE_X + (SPRITE_W * 2)
    sta HPOSP2

    ; Quadruple width (x4 = 3) for all 3 players
    lda #3
    sta SIZEP0
    sta SIZEP1
    sta SIZEP2

    ; Green color for all 3 players
    lda #SPRITE_COL
    sta PCOLR0
    sta COLPM0
    sta PCOLR1
    sta COLPM1
    sta PCOLR2
    sta COLPM2

    ; Priority: Player 0-3 in front of playfield
    lda #$01
    sta GPRIOR
    sta PRIOR

    ; Enable player display in GTIA
    lda #2
    sta GRACTL
    sta HITCLR

    ; Set Display List pointer (shadow and hardware)
    lda #<dlist_title
    sta SDLSTL
    sta DLISTL
    lda #>dlist_title
    sta SDLSTH
    sta DLISTH

    ; Colors for Graphics 8 / ANTIC Mode F:
    lda #$0E
    sta COLOR2
    sta COLPF2

    lda #$00
    sta COLOR1
    sta COLPF1
    sta COLOR4
    sta COLBK

    ; Enable playfield DMA + single-line PMG + Player DMA (%00111010 = $3A)
    lda #$3A
    sta SDMCTL
    sta DMACTL
    rts

title_run
    lda fire_pressed
    beq @+
    lda #0
    sta fire_pressed
    lda #STATE_INTRO
    sta game_state
@   rts
