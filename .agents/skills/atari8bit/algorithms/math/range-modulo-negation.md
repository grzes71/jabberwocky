# Range Modulo Negation

## 10.3 Modulo, Range, Negation

### Modulo 255

For a 16-bit value `n = 256*hi + lo`, use the identity:

```text
n mod 255 = (hi + lo) mod 255
```

The modulus 255 is special because 256 = 255 + 1. The standard 5-byte
implementation is exact for all 16-bit inputs (verified over 0..65535) and
returns a result in `$00..$FE`:

```asm
; A = (256*HI + LO) mod 255   (8 bytes of code, 11 cycles)
mod255  clc
        lda   LO
        adc   HI
        adc   #1
        sbc   #0
        rts
```

`HI+LO` is a 9-bit value (`$000..$1FE`) held in A plus carry, so `ADC #1`
performs a second `HI+LO` sum. Adding 1 leaves carry set when that second sum is
exactly 255 (`0 mod 255`); when carry is clear the `+1` is undone by `SBC #0`,
leaving `$00..$FE`.

### Range-clamp `[LO..HI]`

```asm
; clamp A to [LO..HI]
range_clamp
        cmp   #LO
        bcs   @check_hi
        lda   #LO
        rts
@check_hi
        cmp   #HI+1
        bcc   @in_range
        lda   #HI
@in_range
        rts
```

### Negation

```asm
; 16-bit two's-complement negate in place
neg_16b
        lda   value
        eor   #$ff
        clc
        adc   #1
        sta   value
        lda   value+1
        eor   #$ff
        adc   #0
        sta   value+1
```

### Carry setup

On NMOS 6502 there is no `BIT #imm`; use `SEC`/`CLC` when you need a defined
carry input. On 65C02/65816, `BIT #imm` still does not load carry; it only
updates Z from `A & imm`.

---
