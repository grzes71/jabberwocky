# Flags

## 11.3 Flag Manipulation (SEC / CLC / SEI / CLI / CLV)

### Carry and interrupt-mask control

```asm
        sec                    ; C = 1
        clc                    ; C = 0
        sei                    ; I = 1  (mask IRQs)
        cli                    ; I = 0  (allow IRQs)
        clv                    ; V = 0  (there is no SEV: to set V, use BIT)
```

`SBC`/`CMP` treat carry as "no borrow", so an unsigned subtraction chain starts
with `SEC`:

```asm
        sec
        sbc   value            ; A = A - value
```

`ASL`/`LSR`/`ROL`/`ROR`/`ADC`/`SBC`/`CMP` all write carry; `STA`, `STX`, `STY`,
`TAX`, `TAY`, `INX`/`INY`/`DEX`/`DEY` and the flag instructions above do not.
That is why "set carry once, then use a chain of shifts" works.

### BIT: N/V/Z from memory without touching A

`BIT <zp>` / `BIT <abs>` copy the operand's bit 7 into N and bit 6 into V, and
set Z from `A AND operand`. A is not modified, and carry is not set:

```asm
        bit   flags            ; N = bit7, V = bit6, Z = (A & flags) == 0
```

A byte whose bit 6 is set (for example the `RTS` opcode `$60`) therefore gives a
one-instruction `V = 1`:

```asm
        bit   v_source
v_source rts                   ; $60 -> V = 1, N = 0
```

The NMOS 6502 has no `BIT #imm`. The usual workaround is a zero-page table of
power-of-two constants (`$01,$02,$04,$08,$10,$20,$40,$80`), so `BIT zp` can test
any single bit:

```asm
        bit   bit_tab+7        ; Z = (A & $80) == 0
```

On 65C02/65816 a real `BIT #imm` exists, but it only updates Z from `A & imm`
(see `math/65816-math.md`); it does not load N/V from the operand.

---
