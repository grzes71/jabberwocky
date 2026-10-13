# Vbi Dli

## §6  NVBLNV — Deferred VBI via SETVBV/XITVBV

Register a deferred VBI with `SETVBV`, and exit it with `XITVBV` rather than
`RTI` so the OS completes the normal VBI chain correctly.

```asm
        ; Register deferred VBI (do this once at startup)
        ldx #>vbi_deferred
        ldy #<vbi_deferred
        lda #$07               ; 7 = deferred vertical blank
        jsr SETVBV

vbi_deferred
        ; ... VBI work ...
        jmp XITVBV
```

- **Immediate VBI** (`A=6` to `SETVBV`) should chain to `SYSVBV`.
- **Deferred VBI** (`A=7` to `SETVBV`) should chain to `XITVBV`.
- If your VBI routine pushes anything on the stack itself, pop it before the
  final jump.

Using `SETVBV` avoids races while the OS is already servicing VBI.
