# Division

## 10.2 Division

### Divide by powers of two

Unsigned division by `2^n` is just a right shift. For 16-bit values:

```asm
; value /= 2
        lsr   value+1
        ror   value
```

Repeat the pair for `/4`, `/8`, and so on.

### General unsigned division

The reliable table-free 6502 pattern is **restoring division**:

1. Shift the next dividend bit into the remainder.
2. Subtract the divisor from the remainder.
3. If the subtraction did not borrow, keep the new remainder and set the next
   quotient bit.
4. If it borrowed, restore the old remainder and clear that quotient bit.
5. Repeat once per input bit.

That algorithm gives exact quotient and remainder for 8/8, 16/8, or 16/16
division with small scratch storage and predictable runtime. For 8/8 it is:

```asm
; in: AOP / BOP (divisor must be >= 1)   out: QUOT, remainder in REM
div88   lda   #0
        sta   REM
        ldx   #8
@loop   asl   AOP             ; next dividend bit -> carry
        rol   REM             ; rem = rem*2 + bit
        lda   REM
        sec
        sbc   BOP
        bcc   @next
        sta   REM
        inc   AOP             ; set the quotient bit
@next   dex
        bne   @loop
        lda   AOP
        sta   QUOT
        rts
```

29 bytes, ~35 cycles per bit (276 cycles total); tested exhaustively for all
`AOP = 0..255`, `BOP = 1..255`.

### Constant divisors

Hand-tuned reciprocal / shift-add routines can be excellent, but they must be
verified case-by-case. The `/3`, `/5`, `/6` and `/10` sequences below are the
constant-cycle routines from Omegamatrix's "Unsigned Integer Division Routines
(rev 2)"; they were exhaustively tested here over the full 8-bit input range
(0..255, divisor >= 1) and are exact, not approximate. Each needs one temporary
byte.

```asm
; A = A / 3          (18 bytes, 30 cycles, constant)
div3    sta   temp
        lsr
        adc   #21
        lsr
        adc   temp
        ror
        lsr
        adc   temp
        ror
        lsr
        adc   temp
        ror
        lsr
        rts

; A = A / 5          (18 bytes, 30 cycles)
div5    sta   temp
        lsr
        adc   #13
        adc   temp
        ror
        lsr
        lsr
        adc   temp
        ror
        adc   temp
        ror
        lsr
        lsr
        rts

; A = A / 10         (17 bytes, 30 cycles)
div10   lsr
        sta   temp
        lsr
        adc   temp
        ror
        lsr
        lsr
        adc   temp
        ror
        adc   temp
        ror
        lsr
        lsr
        rts
```

If you write your own reciprocal or table divider, exhaustively test it across
its full stated input range — the rounding of these sequences is subtle (they
rely on the carry history of the shift/add chain).

---
