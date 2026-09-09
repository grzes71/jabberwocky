; ==============================================================================
; SCENES/TEXT_UTILS.ASM — Helpers for Text Rendering (ANTIC Mode 2 / Gr.0)
; ==============================================================================

; Clear 960 bytes of STUB_VRAM with space character (display code 0)
clear_stub_vram
    lda #0
    ldx #0
@   sta STUB_VRAM,x
    sta STUB_VRAM+$100,x
    sta STUB_VRAM+$200,x
    cpx #$C0            ; 960 - 768 = 192 ($C0)
    bcs @+
    sta STUB_VRAM+$300,x
@   inx
    bne @-1
    rts

; Disable PMG display and reset GTIA sprite registers
disable_pmg
    lda #0
    sta GRACTL
    sta GRAFP0
    sta GRAFP1
    sta GRAFP2
    sta GRAFP3
    sta GRAFM
    sta HPOSP0
    sta HPOSP1
    sta HPOSP2
    sta HPOSP3
    sta HPOSM0
    sta HPOSM1
    sta HPOSM2
    sta HPOSM3
    sta SIZEM
    rts

; Print text string at (X = row 0..23, Y = col 0..39)
; String format: [1 byte length, followed by internal display codes]
; Pointer to string must be in PTR_SRC beforehand.
print_at
    ; Calculate DST address = STUB_VRAM + row_offset[X] + Y
    lda stub_row_lo,x
    clc
    sty ZP_TMP
    adc ZP_TMP
    sta PTR_DST
    lda stub_row_hi,x
    adc #0
    sta PTR_DST+1

    ; Read length
    ldy #0
    lda (PTR_SRC),y
    beq @+
    tax                 ; X = length counter

    ldy #1
@   lda (PTR_SRC),y
    dey
    sta (PTR_DST),y
    iny
    iny
    dex
    bne @-

@   rts

; Row offset lookup tables
stub_row_lo
    :24 dta <(STUB_VRAM + (# * 40))

stub_row_hi
    :24 dta >(STUB_VRAM + (# * 40))
