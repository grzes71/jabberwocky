# 6502 Basics

## 1.1  MOS 6502 — Flags, Cycle Timing, DMA Contention

### Clock speeds

| Standard | CPU clock | Cycles / scan line | Cycles / frame |
|---|---|---|---|
| NTSC | 1.789 773 MHz (½ color clock) | 114 | 29 868 |
| PAL | 1.773 447 MHz | 114 | 35 568 |

### Flags (P register)

| Bit | Flag | Description |
|---|---|---|
| 0 | C — Carry | No-borrow indicator; C=1 for SBC means no borrow in |
| 1 | Z — Zero | Set when result = $00 |
| 2 | I — Interrupt mask | Set=IRQs masked; set on reset; NMIs unaffected |
| 3 | D — Decimal | BCD correction active for ADC/SBC only |
| 4 | B — Break | Pushed set for BRK, cleared for IRQ/NMI; never directly readable |
| 5 | — | Always reads 1 in P; reused as M flag on 65C816 native |
| 6 | V — Overflow | Signed overflow during ADC/SBC |
| 7 | N — Negative | Copy of bit 7 of last result |

**Critical nuance — D flag:** NMOS 6502 does NOT auto-clear D on entry to an interrupt. Always `CLD` in interrupt handlers that use ADC/SBC.

### Dead memory cycles

These extra bus cycles still consume time. Avoid them when touching side-effect I/O registers or racing exact display timing:

```
; ❌ Bad in ISR context: INC abs does a write-back dummy cycle
INC $D40E         ; NMIEN — two write cycles; risky at exact cycle deadlines

; ✅ Fine: LDA zp does not produce a dead cycle
LDA $07           ; zero-page read — no dead cycle
```

Common sources: read-modify-write opcodes (`INC`, `DEC`, `ASL`, `LSR`, `ROL`, `ROR`) and indexed reads that cross a page boundary. Taken branches add one cycle; crossing a page adds one more.

**Dangerous addresses for dead-cycle writes:** PIA `$D300–$D3FF` (reads clear pending IRQs); cartridge control `$D500–$D5FF`; PBI `$D100–$D1FE` and `$D600–$D7FF`.

### Page-crossing penalty

Abs indexed reads (`LDA abs,X`, `AND abs,Y`, `(zp),Y`) speculate the fetch: read low-byte page first then retry at correct page if carry. Takes +1 cycle on page-cross. **Write operations always take the +1 cycle** — there is no speculative write.

Branches that cross a page take 4 cycles instead of 3 — even including BEQ issued near the target.

ANTIC DMA steals CPU cycles; exact per-mode budgets belong to the ANTIC timing
tables in `hardware/antic/`.
