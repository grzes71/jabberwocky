# Undocumented Opcodes

## 1.2  Undocumented 6502 Opcodes

All NMOS-only. None operate on the 65C02/65C816. Opcodes from the the reference manual full opcode table.

---

### Merged RMW + ALU opcodes (stable)

| Canonical name | Opcode | BF equivalent | Description |
|---|---|---|---|
| DCP | `$C3/$C7/$CF/$D3/$D7/$DB/$DF` | DEC+CMP | Decrement memory, then compare A with result |
| ISC / ISB | `$E3/$E7/$EF/$F3/$F7/$FB/$FF` | INC+SBC | Increment memory, then `SBC`; decimal-sensitive |
| SLO | `$03/$07/$0F/$13/$17/$1B/$1F` | ASL+ORA | Shift left, then ORA; N/Z from final A |
| RLA | `$23/$27/$2F/$33/$37/$3B/$3F` | ROL+AND | Rotate left, then AND |
| SRE | `$43/$47/$4F/$53/$57/$5B/$5F` | LSR+EOR | Shift right, then EOR |
| RRA | `$63/$67/$6F/$73/$77/$7B/$7F` | ROR+ADC | Rotate right, then `ADC`; decimal-sensitive |

Full opcode map (all 256 encodings): see the the reference manual full opcode map (Tables 2/3/4).

---

### Other stable undocumented opcodes

| Name | Opcode | Description |
|---|---|---|
| **LAX** | `$A3/$A7/$AF/$B3/$B7/$BF` | Load A and X together; N/Z set |
| **SAX** | `$83/$87/$8F/$97` | Store `A AND X`; no flags |
| **ANC** | `$0B/$2B` | `AND #imm`; copy result bit 7 into C |
| **ALR / ASR** | `$4B` | `AND #imm`, then `LSR A` |
| **ARR** | `$6B` | `AND #imm`, then `ROR A`; V/C are chip-sensitive |
| **XAA / ANE** | `$8B` | `A = X AND imm` plus analog-bus effects; unstable |
| **AHX / SHA** | `$93/$9F` | Store `(A AND X AND high+1)`; unstable |
| **TAS / SHS** | `$9B` | `S = A AND X`, then store `S AND high+1`; unstable |
| **SHX** | `$9E` | Store `X AND high+1`; unstable |
| **SHY** | `$9C` | Store `Y AND high+1`; unstable |
| **LAS** | `$BB` | `A = X = S = mem AND S`; N/Z set |
| **AXS / SBX** | `$CB` | `X = (A AND X) - imm`; C acts like CMP |
| **LXA** | `$AB` | Load A/X from immediate+bus mix; unstable |

---

### Opcodes that lock up the CPU

```
KIL  $02 $12 $22 $32 $42 $52 $62 $72 $92 $B2 $D2 $F2
```
**Never branch to or fall through a KIL opcode; only RESET restores execution.**

---
