# Loop Idioms

## 11.4 Negative-Index Loop

Using negative-style X-indexing to descend through a table or array:

```asm
        ldx   #$3F
@loop   lda   table,x
        dex
        bpl   @loop             ; BPL = until X goes negative; covers #$3F..0

; exact 128-iteration variant
        ldx   #$7F
@loop2  lda   table,x
        dex
        bpl   @loop2            ; covers #$7F..$00 (128 iterations)
```

`DEX`/`DEY`/`INX`/`INY` set N and Z but **not** carry, so a descending loop that
continues "until carry wraps" does not exist: use `BPL`/`BMI` on the index, or
compare explicitly. The two forms above end naturally because the sign bit of X
changes exactly once.

---
