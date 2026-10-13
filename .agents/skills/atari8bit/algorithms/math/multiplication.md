# Multiplication

## 10.1 Multiplication

### Multiply by 3 (16-bit)

```asm
mul3    lda   num
        asl
        sta   result
        lda   num+1
        rol
        sta   result+1
        clc
        lda   result
        adc   num
        sta   result
        lda   result+1
        adc   num+1
        sta   result+1
```

### Multiply by 10 (16-bit)

This version forms `10*x = 8*x + 2*x`:

```asm
mul10   lda   num
        asl
        sta   tmp
        sta   result
        lda   num+1
        rol
        sta   tmp+1
        sta   result+1
        asl   result
        rol   result+1
        asl   result
        rol   result+1        ; result = 8*x
        clc
        lda   result
        adc   tmp
        sta   result
        lda   result+1
        adc   tmp+1
        sta   result+1        ; result = 10*x
```

### Quarter-square multiply

The exact unsigned identity is:

```text
ab = floor((a+b)^2 / 4) - floor((a-b)^2 / 4)
```

That is why quarter-square tables store `floor(n*n/4)`. For 8-bit operands,
`a+b` ranges up to 510, so an exact implementation must preserve the **ninth**
bit of that index. A routine that simply puts `a+b` into X or Y without extra
handling will fail for sums 256..510.

### Generic products

- Use a shift-add loop for general 8×8, 16×8, or 16×16 products when table
  memory is not acceptable.
- Use quarter-square or square-table methods when many multiplies justify the
  LUT cost.
- A generic 65816 still has no built-in hardware multiplier; treat any
  `$4202/$4203` example as platform-specific, not CPU-generic.

---
