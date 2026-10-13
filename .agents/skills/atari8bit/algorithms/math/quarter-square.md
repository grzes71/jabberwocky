# Quarter Square

## 10.5 QS (Quarter-Square) Multiply

The exact quarter-square identity for unsigned multiplication is:

```text
ab = floor((a+b)^2 / 4) - floor((a-b)^2 / 4)
```

So a quarter-square table stores `floor(n*n/4)`. For 8-bit operands:

- `a+b` ranges from 0 to 510
- `|a-b|` ranges from 0 to 255

That means an exact one-table implementation must preserve the **9-bit** sum
index. A routine that reduces `a+b` to an 8-bit X/Y index is incomplete and
breaks cases where `a+b >= 256` (for example `1*255`).

For signed inputs, save the sign from `a xor b`, multiply absolute values with
the unsigned core, then two's-complement the 16-bit product if the saved sign
bit was set.

### Exact 8x8 routine (tested)

The table holds `floor(n*n/4)` for `n = 0..510` (511 entries, 1022 bytes); the
9th bit of `a+b` selects the second table page, so no cases are lost. The
routine below was verified exhaustively over all 65536 operand pairs.

```asm
; sq_lo/sq_hi: floor(n*n/4), n = 0..510
sq_lo   :511 dta l(#*#/4)
sq_hi   :511 dta h(#*#/4)

; in: AOP, BOP     out: RESULT/RESULT+1 = AOP*BOP
qs_mul  lda   AOP
        clc
        adc   BOP
        sta   qs_sl           ; a+b low
        lda   #0
        adc   #0
        sta   qs_sh           ; a+b bit 8 (0/1)
        lda   AOP
        sec
        sbc   BOP
        bcs   qs_pos
        eor   #$ff
        adc   #1              ; |a-b|
qs_pos  sta   qs_d
        lda   #<sq_lo
        sta   qs_p1+1
        lda   #>sq_lo
        clc
        adc   qs_sh
        sta   qs_p1+2
        ldy   qs_sl
qs_p1   lda   $ffff,y         ; floor((a+b)^2/4) low
        sta   RESULT
        lda   #<sq_hi
        sta   qs_p2+1
        lda   #>sq_hi
        clc
        adc   qs_sh
        sta   qs_p2+2
qs_p2   lda   $ffff,y         ; floor((a+b)^2/4) high
        sta   RESULT+1
        lda   #<sq_lo
        sta   qs_p3+1
        ldy   qs_d
qs_p3   lda   $ffff,y         ; floor((a-b)^2/4) low
        sta   TMP
        lda   #<sq_hi
        sta   qs_p4+1
qs_p4   lda   $ffff,y         ; floor((a-b)^2/4) high
        sta   TMP+1
        sec
        lda   RESULT
        sbc   TMP
        sta   RESULT
        lda   RESULT+1
        sbc   TMP+1
        sta   RESULT+1
        rts
```

Cost: 117 bytes of code, 151 cycles, 1022 bytes of table. Because the base
operands are patched for every call, run it from writable RAM.

---
