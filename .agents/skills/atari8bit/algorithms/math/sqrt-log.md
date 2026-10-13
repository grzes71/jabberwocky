# Sqrt Log

## 10.7 16-bit Sqrt + 8-bit Log Table

For exact `sqrt(word)`, the standard table-free fallback is a restoring
square-root routine. Note that it consumes **two** radicand bits per root bit,
so a 16-bit input needs eight iterations:

```asm
; contract:
; in:  NUMH:NUML unsigned 16-bit
; out: ROOT = floor(sqrt(NUMH:NUML)), REM = remainder
; invariant: original = ROOT*ROOT + REM

sqrt16  lda   #0
        sta   ROOT
        sta   ROOT+1
        sta   REM
        sta   REM+1
        ldx   #8               ; 8 root bits = 16 radicand bits
@loop   asl   NUML             ; shift two radicand bits into the remainder
        rol   NUMH
        rol   REM
        rol   REM+1
        asl   NUML
        rol   NUMH
        rol   REM
        rol   REM+1
        asl   ROOT             ; root <<= 1
        rol   ROOT+1
        lda   ROOT
        sta   TMP
        lda   ROOT+1
        sta   TMP+1
        asl   TMP              ; trial = 2*root + 1
        rol   TMP+1
        lda   TMP
        ora   #$01
        sta   TMP
        lda   REM+1
        cmp   TMP+1
        bcc   @next
        bne   @sub
        lda   REM
        cmp   TMP
        bcc   @next
@sub    lda   REM
        sec
        sbc   TMP
        sta   REM
        lda   REM+1
        sbc   TMP+1
        sta   REM+1
        inc   ROOT
@next   dex
        bne   @loop
        rts
```

83 bytes of code (all operands zero page), ~854 cycles. Tested against
`isqrt()` for all 65536 inputs, including the `ROOT*ROOT + REM = N` invariant.

For 8-bit logarithms, small LUTs are usually **approximations**, not exact
integer `log2`. Always special-case `0`, because `log2(0)` is undefined.

If a table is indexed by `n >> 1` or some other reduced form, document the
scaling and interpolation clearly so callers do not mistake the result for an
exact logarithm.

---
