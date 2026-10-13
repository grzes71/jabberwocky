# Shifts Rotates

## 11.2 Bit Rotation Idioms (ROL / ROR / ASL / LSR)

### 9-bit rotate through carry

`ROL`/`ROR` are 9-bit rotates: carry is the extra bit (1 byte, 2 cycles):

```asm
        rol                    ; C -> bit0, bit7 -> C
        ror                    ; C -> bit7, bit0 -> C
```

Chain the memory forms for multi-byte rotates through carry:

```asm
        clc
        rol   lo               ; 16-bit rotate left through carry
        rol   hi
; 5 bytes, 12 cycles

        sec
        ror   hi               ; 16-bit rotate right through carry
        ror   lo
```

There is no `ROL X` / `ASL X`: the shift and rotate instructions only have
accumulator and memory addressing modes, so use a memory byte (or move X out
first).

### True 8-bit rotate left / right

An 8-bit rotate must not use the incoming carry, so preload it:

```asm
; 8-bit rotate left, A only
        cmp   #$80             ; C = bit7
        rol                    ; bit7 -> bit0
; 3 bytes, 4 cycles

; 8-bit rotate right, A only
        pha
        lsr                    ; C = bit0
        pla                    ; restores A; carry is preserved
        ror                    ; bit0 -> bit7
; 4 bytes, 11 cycles
```

### Two-position rotates (the carry-return idiom)

`CLC` + `ASL` + `ROL` and `SEC` + `LSR` + `ROR` rotate by **two** positions, not
one: the bit shifted out by the first shift re-enters at the other end after the
second.

```asm
        clc
        asl
        rol                    ; 8-bit rotate left by 2
; 3 bytes, 6 cycles

        sec
        lsr
        ror                    ; 8-bit rotate right by 2
; 3 bytes, 6 cycles
```

### 9-bit rotate-left via stack

Rotate `carry:A` left and still hand the caller its original carry back:

```asm
        php                    ; save P, including C
        asl                    ; bit7 -> C
        rol   buffer           ; buffer holds the upper bits of the rotated value
        plp                    ; restore the original carry
```

`PHP`=3, `ASL`=2, `ROL zp`=5, `PLP`=4, so 14 cycles in total. If the outgoing bit
is not needed, drop `PHP`/`PLP` and use `ASL` + `ROL` for a plain 9-bit shift
left of `buffer:A`.

### Garth Wilson nybble-swap (8 bytes, 12 cycles, A-only)

Each `ASL` + `ADC #$80` + `ROL` triple is a 2-bit rotate left of A, so two triples
swap the nibbles with no temporary byte, stack use, or table:

```asm
nyb_swap
        asl
        adc   #$80
        rol
        asl
        adc   #$80
        rol
; 8 bytes, 12 cycles; only A and the flags are used
```

### Two-byte rotate (16-bit)

```asm
        clc
        rol   lo               ; rotate C:hi:lo left through carry
        rol   hi

; ROR variant:
        sec
        ror   hi
        ror   lo
```

---
