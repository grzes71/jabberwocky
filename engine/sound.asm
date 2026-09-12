; ==============================================================================
; ENGINE/SOUND.ASM — Sound Effects & POKEY Audio Tables
; Target: Atari 800XL / 65XE
; Placed in high RAM (after WORLD_DATA / CHARSET_ANIM) to preserve CODE space.
; ==============================================================================

; --- Explosion Sound Tables (POKEY Ch 1 & 2 across 24 frames, ~0.5s) ---
; Channel 1: Low-frequency boom (distortion $00 = 17+5 bit noise rumble)
expl_snd_audf1
    dta $24, $2C, $38, $48, $5C, $70, $84, $98, $A8, $B8, $C4, $D0
    dta $DC, $E4, $EC, $F0, $F4, $F8, $FC, $FC, $FC, $FC, $FC, $FC

expl_snd_audc1
    dta $0F, $0F, $0E, $0E, $0D, $0D, $0C, $0B, $0A, $09, $08, $07
    dta $06, $05, $05, $04, $03, $03, $02, $02, $01, $01, $00, $00

; Channel 2: Harsh blast & crackle (distortion $80 = 17 bit white noise)
expl_snd_audf2
    dta $10, $14, $1A, $22, $2C, $38, $44, $50, $60, $70, $80, $90
    dta $A0, $B0, $C0, $D0, $D8, $E0, $E8, $F0, $F8, $F8, $F8, $F8

expl_snd_audc2
    dta $8E, $8F, $8E, $8D, $8C, $8B, $8A, $89, $88, $87, $86, $85
    dta $84, $83, $83, $82, $82, $81, $81, $80, $80, $80, $80, $80

; --- Crash Sound Tables (POKEY Ch 1 & 2 across 24 frames, ~0.5s) ---
; Channel 1: Harsh metallic impact crunch (distortion $20 = 5-bit poly) decaying to deep rumble ($00)
crash_snd_audf1
    dta $08, $0C, $14, $1E, $28, $38, $4C, $64, $7C, $94, $AC, $C0
    dta $D0, $DC, $E8, $F0, $F8, $FC, $FC, $FC, $FC, $FC, $FC, $FC

crash_snd_audc1
    dta $2F, $2F, $2E, $2D, $0D, $0C, $0B, $0A, $08, $07, $06, $05
    dta $04, $03, $03, $02, $02, $01, $01, $00, $00, $00, $00, $00

; Channel 2: Sharp impact snap and shattering debris (distortion $80 = white noise)
crash_snd_audf2
    dta $04, $06, $0A, $12, $1C, $28, $38, $4C, $60, $74, $88, $9C
    dta $B0, $C0, $D0, $DC, $E8, $F0, $F8, $F8, $F8, $F8, $F8, $F8

crash_snd_audc2
    dta $8F, $8F, $8E, $8D, $8C, $8A, $88, $87, $86, $85, $84, $83
    dta $82, $82, $81, $81, $80, $80, $80, $80, $80, $80, $80, $80
