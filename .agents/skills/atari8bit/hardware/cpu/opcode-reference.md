# Opcode Reference

## 1.7  Opcode Quick Reference

| Addressing mode | Cycles | Notes |
|---|---|---|
| Implied / accumulator | 2 | `TXA`, `INX`, `DEY` … |
| Immediate (`#imm`) | 2 | `LDA #$FF` … |
| Zero page (`$NN`) | 3 | Read or write |
| Zero page,X / zero page,Y | 4 | Indexed zero page |
| Absolute (`$NNNN`) | 4 | Read or write |
| Absolute,X / absolute,Y read | 4 (+1 if page cross) | Applies to loads/logic ops |
| Absolute,X / absolute,Y write | 5 | Writes always pay the extra cycle |
| `(zp,X)` | 6 | Indexed-indirect |
| `(zp),Y` read / write | 5 (+1 if page cross) / 6 | Indirect-indexed |
| `JMP abs` / `JMP (abs)` | 3 / 5 | NMOS indirect JMP wraps at `$xxFF` |
| RMW opcode (`INC`, `ASL`, `ROR` …) | zp 5, abs 6, zp,X 6, abs,X 7 | Extra dummy write included |
| Branch | 2 not taken / 3 taken / 4 taken + page cross | |
| BRK / IRQ / NMI entry | 7 | |
| JSR / RTS / RTI | 6 / 6 / 6 | |
| PHP / PLP | 3 / 4 | |

| Opcode class | Cycle range | Comments |
|---|---|---|
| `LDA/STA/STY/STX` absolute | 4 | |
| `ADC / SBC` (accumulator) | 2 | +1 in decimal mode on 65C02 |
| `CMP / CPX / CPY` immediate | 2 | |
| `CMP` zero-page | 3 | |
| `BEQ/BNE/BCC/BCS` | 2 (not taken) / 3 (taken) / 4 (page-cross) | |
| `ROL/ROR/ASL/LSR` / memory | 6 | 5 on zero page |
| `BIT` zero-page / absolute | 3 / 4 | Zero-page form is 65C02-only |

**NMOS-only page-cross penalty summary**:
- Reads (`LDA abs,Y`, `AND abs,Y`, etc.) speculate on page-cross: read wrong page → carry → retry (5 cycles total if wrong).
- Writes (`STA abs,Y`) always 5 cycles speculatively; no retry; the first cycle is a dummy-read.
- `JMP (abs)` has a well-documented hardware bug when the low byte of the target address is `$FF` — the high byte is fetched from `$xx00` instead of `$xx+1`.

---

*Primary references: the ANTIC/CPU hardware documentation (De Re Atari, Altirra hardware reference); see `hardware/antic.md` and `hardware/cpu.md` for the full maps.*
