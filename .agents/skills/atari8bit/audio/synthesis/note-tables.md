# Note Tables

## PAL Note Frequency Table (AUDF Values)

The following table provides pre-computed AUDF divider values for musical notes under the PAL POKEY base clock (63.337 kHz, 8-bit mode). Values are computed as `AUDF = round(63337 / (2 × f_note)) − 1`.

| Note | AUDF | Note | AUDF | Note | AUDF | Note | AUDF |
|------|------|------|------|------|------|------|------|
| H₀   | $FF  | C₂   | $78  | C₃   | $3C  | C₄   | $1D  |
| C₁   | $F1  | C♯₂  | $71  | C♯₃  | $38  | C♯₄  | $1C  |
| C♯₁  | $E3  | D₂   | $6B  | D₃   | $35  | D₄   | $1A  |
| D₁   | $D7  | D♯₂  | $65  | D♯₃  | $32  | D♯₄  | $18  |
| D♯₁  | $CB  | E₂   | $5F  | E₃   | $2F  | E₄   | $17  |
| E₁   | $BF  | F₂   | $5A  | F₃   | $2C  | F₄   | $16  |
| F₁   | $B4  | F♯₂  | $55  | F♯₃  | $2A  | F♯₄  | $14  |
| F♯₁  | $AA  | G₂   | $50  | G₃   | $27  | G₄   | $13  |
| G₁   | $A1  | G♯₂  | $4B  | G♯₃  | $25  | G♯₄  | $12  |
| G♯₁  | $98  | A₂   | $47  | A₃   | $23  | A₄   | $11  |
| A₁   | $8F  | A♯₂  | $43  | A♯₃  | $21  | A♯₄  | $10  |
| A♯₁  | $87  | H₂   | $3F  | H₃   | $1F  | H₄   | $0F  |
| H₁   | $7F  |      |      |      |      |      |      |

| Note | AUDF | Note | AUDF | Note | AUDF | Note | AUDF |
|------|------|------|------|------|------|------|------|
| C₅   | $0E  | C₆   | $07  | C₇   | $03  | C₈   | $01  |
| C♯₅  | $0D  | C♯₆  | $06  | C♯₇  | $03  | C♯₈  | $01  |
| D₅   | $0C  | D₆   | $06  | D₇   | $02  | D₈   | $01  |
| D♯₅  | $0C  | D♯₆  | $05  | D♯₇  | $02  | D♯₈  | $01  |
| E₅   | $0B  | E₆   | $05  | E₇   | $02  | E₈   | $01  |
| F₅   | $0A  | F₆   | $05  | F₇   | $02  | F₈   | $00  |
| F♯₅  | $0A  | F♯₆  | $04  | F♯₇  | $02  | F♯₈  | $00  |
| G₅   | $09  | G₆   | $04  | G₇   | $02  | G₈   | $00  |
| G♯₅  | $09  | G♯₆  | $04  | G♯₇  | $01  | G♯₈  | $00  |
| A₅   | $08  | A₆   | $03  | A₇   | $01  | A₈   | $00  |
| A♯₅  | $07  | A♯₆  | $03  | A♯₇  | $01  | A♯₈  | $00  |
| H₅   | $07  | H₆   | $03  | H₇   | $01  | H₈   | $00  |

The European notation uses H for B-natural and B for B-flat. The following B-flat aliases match the H entries above:

```asm
B_0 equ H_0    B_1 equ H_1    B_2 equ H_2    B_3 equ H_3
B_4 equ H_4    B_5 equ H_5    B_6 equ H_6    B_7 equ H_7    B_8 equ H_8
```

### Usage

The octave numbers in this table follow the 8-bit divider range (the first entry,
`AUDF = $FF`, is the lowest pitch the 64 kHz / 15 kHz path can produce), not
scientific pitch notation. In scientific terms middle C (261.6 Hz) is `C₂ = $78`
and A₄ = 440 Hz is `A₂ = $47`.

```asm
LDA #C_2          ; $78 — middle C (261.6 Hz) on PAL
STA AUDF1
LDA #$A8          ; distortion 5 (pure tone), volume 8
STA AUDC1
```

For 16-bit paired mode, compute the combined divider value instead (see
`frequency-tuning.md`); the 8-bit table above applies to the 63.337 kHz base clock only.

---
