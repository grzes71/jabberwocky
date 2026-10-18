# Banking Extended Ram

## 2.3  BANK Switching & Extended Memory (XL/XE $4000–$7FFF)

On XL/XE computers, `PORTB ($D301)` controls ROM visibility and, on 130XE-class machines, the banked 16K window at `$4000-$7FFF`.

### PORTB bits for ROM / 130XE bank control

| Bit | Meaning | Common interpretation |
|---|---|---|
| 0 | OS ROM control | `1` = OS ROM visible, `0` = underlying RAM visible at `$C000-$CFFF` and `$D800-$FFFF` |
| 1 | BASIC ROM control | `0` = BASIC visible at `$A000-$BFFF`, `1` = BASIC off / RAM visible |
| 2-3 | 130XE bank number | Select one of four 16K banks for the banked window |
| 4 | CPU bank-window select | `1` = main RAM at `$4000-$7FFF`, `0` = selected extended bank for CPU |
| 5 | ANTIC bank-window select | `1` = ANTIC sees main RAM, `0` = ANTIC sees the selected extended bank |
| 6 | XEGS built-in game ROM | On XEGS only: `0` = game ROM visible at `$A000-$BFFF` when BASIC is off |
| 7 | Self-test control | Preserve unless you intentionally enter or leave self-test |

`PORTB` is machine-dependent beyond the stock 130XE definition. XEGS and third-party RAM expansions can reuse additional bits, so save the original value and restore it when you are done.

```asm
        ; Example: disable OS and BASIC, preserving all other PORTB state
        lda PORTB
        pha
        and #$FE              ; bit 0 = 0 -> OS off
        ora #$02              ; bit 1 = 1 -> BASIC off
        sta PORTB

        ; ... RAM-only work here ...

        pla
        sta PORTB
```

### 130XE extended RAM window

The stock 130XE provides **four** extra 16K banks. Bits 2-3 select bank 0-3; bit 4 controls whether the CPU sees banked RAM or the normal `$4000-$7FFF` RAM; bit 5 does the same independently for ANTIC.

| Bits 3:2 | Bank |
|---|---|
| `00` | Bank 0 |
| `01` | Bank 1 |
| `10` | Bank 2 |
| `11` | Bank 3 |

### Larger XL/XE expansions

192K, 256K, 320K, 576K, and 1088K expansions typically extend the 130XE idea by reusing more `PORTB` bits. The exact encodings are expansion-specific:

- **RAMBO/Newell-style** boards usually keep the 130XE window at `$4000-$7FFF` but extend the bank number with more `PORTB` bits.
- **Compy Shop / COMPY** boards also provide separate CPU/ANTIC control, but their high-bank encodings differ from RAMBO.
- **576K / 1088K** schemes reuse bits that on a stock XL/XE also affect ROM state, so software must use an expansion-specific table rather than assume one universal formula.

If coexistence with DOS or SpartaDOS X matters, do not run a generic raw-probe routine against extended RAM after DOS has allocated RAM-disk or cache banks.

### Axlon-style extended RAM

Axlon-style expansions for 400/800-class machines bank 16K chunks into `$4000-$7FFF` through a write-only register at `$CFFF`. Original hardware often decodes that register incompletely, so treat it as expansion-specific and restore bank 0 before returning to general code.

### Writes to ROM are silently discarded

Writes to any address currently mapped to ROM (OS, BASIC, self-test, or cartridge) are ignored. There is no write-through into the hidden RAM at the same address.

---
