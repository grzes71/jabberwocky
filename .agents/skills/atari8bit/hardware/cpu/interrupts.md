# Interrupts

## 1.5  Interrupts — IRQ / NMI / BRK

### IRQ (maskable)

- **Level-sensitive** — the IRQ line must remain asserted until the CPU starts
  the interrupt sequence and the source is cleared.
- The IRQ must be **cleared at the device** before `CLI`, else IRQ handler re-enters immediately.
- On the 6502/65C02, **IRQ and BRK share vector `$FFFE/$FFFF`**.
- IRQ, NMI, and BRK all take **7 cycles** from recognition to vector fetch.

### Vector table

| Vector | Address |
|---|---|
| NMI | `$FFFA/$FFFB` |
| RESET | `$FFFC/$FFFD` |
| IRQ / BRK | `$FFFE/$FFFF` |

### NMI (edge‑triggered, non‑maskable)

NMI is edge-triggered on the 6502 family. On Atari systems, ANTIC uses NMI for
DLI and VBI. On the 400/800, the RESET button also appears through the NMI
status bit; on XL/XE, RESET is a separate CPU reset input.

**NMIST (`$D40F`) bit layout**:  
- bit 7 = DLI occurred  
- bit 6 = VBI occurred  
- bit 5 = RNMI / SYSTEM RESET (400/800 only)  
- bit 4–0 = unused / reserved

Write any value to `NMIRES` (same address, write side) after servicing the
interrupt to clear the latched status bits.

**Critical: never set NMIEN bit 7 before `VDSLST` is valid:**

```asm
        lda #<my_dli        ; set vector FIRST
        sta VDSLST
        lda #>my_dli
        sta VDSLST+1
        lda #$C0            ; NMIEN: $40=VBI, $80=DLI
        sta NMIEN           ; NOW enable
```

### BRK edge case

BRK uses the IRQ/BRK vector and pushes **PC+2** plus a status byte with the
stacked **B bit set**. A hardware IRQ pushes the same format byte with **B=0**.
If an NMI arrives while a BRK sequence is already stacking state, the NMI
handler may observe that stacked BRK-format status byte.

---

## 1.6  DLI / VBI practical rules

* DLI and VBI are **NMI sources from ANTIC**, not POKEY IRQs.
* Install `VDSLST` before enabling DLI in `NMIEN`.
* Keep DLI handlers short enough to complete before the next enabled DLI.
* If both NMI and IRQ are pending at an instruction boundary, **NMI wins**;
  the IRQ remains pending if its source is still asserted.

---
