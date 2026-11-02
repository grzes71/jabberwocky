---
name: atari8bit-memory
description: >-
  Atari 8-bit 64 K memory map and chipset register reference. Covers the flat $0000–$FFFF address space, key zero-page and page-2/page-3 OS variables, PIA 6520 PORTA/PORTB/PACTL/PBCTL register table, XL/XE PORTB ROM-banking bits, 130XE extended RAM windowing, and safe zero-page/stack idioms. Use when the user asks about RAM layout, OS variables, PIA registers, PORTB banking, extended RAM, zero page, or stack tricks.
---

# 02 — Memory Map & System Architecture

> **Scope:** 64K flat map ($0000–$FFFF), key OS variables and vectors, PIA 6520, PORTB banking/ROM bits, 130XE-style extended RAM, zero-page idioms, stack rules
> **Key items:** PORTA $D300, PORTB $D301, PACTL/PBCTL $D302/$D303, VDSLST $0200, VVBLKI/VVBLKD $0222/$0224, SDLSTL $0230, HATABS $031A, IOCB $0340

## Purpose

This file covers the memory map and system architecture for the Atari 8-bit in four progressive layers:
1. **Quick-lookup table** — scan or search for the fact you need; jump to the § directly
2. **Reference tables & register maps** — the dense lookup layer most frequently referenced
3. **Working code examples** — verified ASM/pattern snippets
4. **Deep reference notes** — edge cases, caveats, implementation rules

| Out of scope | See instead |
|---|---|
| DMA contention and cycle-stealing budget | §03-antic (ANTIC DMA section) |
| SIO DCB structure and frame format | §07-disk-file (SIO section) |

**Tip:** browse the Quick-lookup table below first; the § labels are clickable in most markdown viewers.

Only low address bits are decoded across much of the hardware page. In particular, the PIA mirrors through `$D300-$D3FF`, and writes to addresses currently mapped to ROM are ignored.

## Quick-lookup

| Need | See § |
|---|---|
| 64 K memory map | §2.1 |
| Zero-page and OS variable examples | §2.1 |
| PIA 6520 register table | §2.1 |
| PORTB OS/BASIC/self-test and 130XE banking bits | §2.3 |
| 130XE / larger XL/XE expansion caveats | §2.3 |
| Zero-page idioms | §2.4 |
| Stack and inline-parameter rules | §2.5 |

---

## 2.1  Full 64 K Memory Map ($0000 – $FFFF)

The Atari 8-bit has a flat 64 K CPU address space. Which ROM or RAM is visible in some ranges depends on the machine family and, on XL/XE machines, `PORTB ($D301)`.

### Map by region

| Region | Purpose |
|---|---|
| `$0000-$00FF` | Zero page — OS variables, DOS/BASIC work areas, user-reserved bytes if your environment allows them |
| `$0100-$01FF` | Hardware stack |
| `$0200-$02FF` | OS database: page-2 vector/IRQ-NMI dispatch table, shadows, timers, color registers, keyboard/display variables — owned by the OS, never by DOS |
| `$0300-$03FF` | OS page 3: SIO `DCB` (`$0300-$030F`), `HATABS`, `IOCB`s, work buffers |
| `$0400-$7FFF` | Main RAM; on 130XE-class machines `$4000-$7FFF` can be replaced by banked extended RAM |
| `$8000-$9FFF` | Cartridge window (`RD4` / right or lower 8K) |
| `$A000-$BFFF` | BASIC ROM, cartridge window (`RD5` / left or upper 8K), or RAM depending on machine and banking |
| `$C000-$CFFF` | XL/XE OS ROM or underlying RAM when OS ROM is banked out |
| `$D000-$D0FF` | GTIA |
| `$D100-$D1FF` | PBI device select / status / device space |
| `$D200-$D2FF` | POKEY |
| `$D300-$D3FF` | PIA 6520 |
| `$D400-$D4FF` | ANTIC |
| `$D500-$D5FF` | Cartridge control space (`CCTL`) on cartridge machines |
| `$D600-$D7FF` | PBI/ECI device register space |
| `$D800-$FFFF` | Math Pack and OS ROM on computer models unless overlaid / banked out |

### Zero page and early RAM landmarks

Zero page is **not** a large free-for-all on Atari systems. The OS, DOS, BASIC, and floating-point package use much of it.

| Address | Name | Purpose |
|---|---|---|
| `$0008` | `WARMST` | Warm-start flag |
| `$000A/$000B` | `DOSVEC` | DOS entry vector |
| `$000C/$000D` | `DOSINI` | DOS initialization vector |
| `$000E/$000F` | `APPMHI` | Application memory high-water mark |
| `$0012-$0014` | `RTCLOK` | 24-bit real-time clock |
| `$0042` | `CRITIC` | Critical I/O section flag |
| `$004D` | `ATRACT` | Attract-mode counter |
| `$004E` | `DRKMSK` | Attract darken mask |
| `$004F` | `COLRSH` | Color-shift state used by attract mode |
| `$006A` | `RAMTOP` | Top of RAM in pages |
| `$0080-$00FF` | Application / FP area | OS reserves this 128-byte block for the application and the floating-point package (`FR0` `$D4`, `FRE` `$DA`, `FR1` `$E0`, `FR2` `$E6`, `FRX` `$EC`) |

Use documented free bytes only, or reserve your own workspace according to the DOS / loader environment you are targeting.

### Page 2 and page 3 landmarks

| Address | Name | Purpose |
|---|---|---|
| `$0200/$0201` | `VDSLST` | DLI vector |
| `$0202/$0203` | `VPRCED` | Serial bus PROCEED IRQ vector |
| `$0204/$0205` | `VINTER` | Serial bus INTERRUPT IRQ vector |
| `$0206/$0207` | `VBREAK` | BRK instruction IRQ vector |
| `$0216/$0217` | `VIMIRQ` | Immediate IRQ vector |
| `$0222/$0223` | `VVBLKI` | Immediate VBI vector |
| `$0224/$0225` | `VVBLKD` | Deferred VBI vector |
| `$022F` | `SDMCTL` | ANTIC DMA shadow |
| `$0230/$0231` | `SDLSTL/SDLSTH` | Display list pointer shadow |
| `$0244` | `COLDST` | Cold-start flag |
| `$026F` | `GPRIOR` | `PRIOR ($D01B)` shadow |
| `$02C4-$02C8` | `COLOR0-COLOR4` | OS color shadows |
| `$02E0/$02E1` | `RUNAD` | Binary load run address |
| `$02E2/$02E3` | `INITAD` | Binary load init address |
| `$02E5/$02E6` | `MEMTOP` | Top of usable RAM pointer |
| `$02EA-$02ED` | `DVSTAT` | Device/disk status buffer (4 bytes) |
| `$02FC` | `CH` | Keyboard character buffer |
| `$0300-$030F` | `DCB` | SIO device control block (`DDEVIC`…`DAUX2`) |
| `$031A` | `HATABS` | Device handler table |
| `$0340-$03BF` | `IOCB0-IOCB7` | Eight 16-byte I/O control blocks |

Page 2 belongs to the OS, not to DOS: it is the OS database — the NMI/IRQ dispatch
vectors above, plus display, color, keyboard and editor shadows. DOS and BASIC keep
their own control blocks in the RAM they allocate and reach the OS through
`DOSVEC`/`DOSINI` (`$000A-$000D`). Page 3 starts with the SIO `DCB` at `$0300`
(`DDEVIC` `$0300`, `DUNIT` `$0301`, `DCOMND` `$0302`, `DSTATS` `$0303`,
`DBUFLO/HI` `$0304/$0305`, `DTIMLO` `$0306`, `DBYTLO/HI` `$0308/$0309`,
`DAUX1/2` `$030A/$030B`); see `system/storage.md` for the command set.

### PIA 6520 (Peripheral Interface Adapter)

Address range: `$D300-$D3FF`; only the low two address bits are decoded, so the four PIA registers repeat throughout the page.

| Register | Address | Function |
|---|---|---|
| `PORTA` | `$D300` | Joystick directions for ports 1 and 2; with PACTL bit 2 clear, accesses DDRA instead |
| `PORTB` | `$D301` | Joystick directions for ports 3 and 4 on 400/800; ROM/RAM/bank control on XL/XE; with PBCTL bit 2 clear, accesses DDRB instead |
| `PACTL` | `$D302` | Port A control register |
| `PBCTL` | `$D303` | Port B control register |

To write `DDRA` or `DDRB`, clear control-register bit 2, write the corresponding port address, then set bit 2 again to return the address to normal port-data access.

---

## 2.2  Power-On / Reset

| Condition | Behavior |
|---|---|
| Power-on | CPU starts through the RESET vector; RAM contents are undefined until initialized |
| 400/800 RESET key | Raises an NMI reported by ANTIC `NMIST` bit 5 and enters the OS warm-start path; RAM is preserved; PIA is **not** reset |
| XL/XE RESET key | Hardware reset of the system; RAM is normally preserved on a warm reset, but hardware and OS shadows/vectors must be reinitialized |

Practical rules:

- Use `WARMST ($08)` and `COLDST ($0244)` together with your own RAM signature if you need to distinguish a recoverable warm reset from a cold start.
- If you own `SDLSTL`, `VDSLST`, or VBI vectors, expect the OS warm-start path to rebuild display/editor state unless you reinstall your values.
- Power-on RAM patterns are not stable data; always initialize anything you depend on.

---

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

That separation is what allows 130XE software to keep the CPU in one bank while ANTIC fetches display data from another.

### Larger XL/XE expansions

192K, 256K, 320K, 576K, and 1088K expansions typically extend the 130XE idea by reusing more `PORTB` bits. The exact encodings are **expansion-specific**:

- **RAMBO/Newell-style** boards usually keep the 130XE window at `$4000-$7FFF` but extend the bank number with more `PORTB` bits.
- **Compy Shop / COMPY** boards also provide separate CPU/ANTIC control, but their high-bank encodings differ from RAMBO.
- **576K / 1088K** schemes reuse bits that on a stock XL/XE also affect ROM state, so software must use an expansion-specific table rather than assume one universal formula.

If coexistence with DOS or SpartaDOS X matters, do not run a generic raw-probe routine against extended RAM after DOS has allocated RAM-disk or cache banks.

### Axlon-style extended RAM

Axlon-style expansions for 400/800-class machines bank 16K chunks into `$4000-$7FFF` through a write-only register at `$CFFF`. Original hardware often decodes that register incompletely, so treat it as expansion-specific and restore bank 0 before returning to general code.

### Writes to ROM are silently discarded

Writes to any address currently mapped to ROM (OS, BASIC, self-test, or cartridge) are ignored. There is no write-through into the hidden RAM at the same address.

---

## 2.4  Zero-Page Idioms

| Idiom | Example | Notes |
|---|---|---|
| Increment 16-bit pointer | `INC ptr` / `BNE skip` / `INC ptr+1` | Increment high byte **only** when low byte wraps |
| Decrement 16-bit pointer | `LDA ptr` / `BNE skip` / `DEC ptr+1` / `skip DEC ptr` | Borrow propagates from low byte |
| Bit flag set/clear | `ORA #$80` / `AND #$7F` | Use explicit masks; assembler-specific `~` syntax is not portable |
| Backward loop | `LDY #n-1` / `...` / `DEY` / `BPL loop` | Standard 0..n-1 reverse walk |
| Fast ISR save | `PHA / TXA / PHA / TYA / PHA` | Stack save is the normal DLI/VBI pattern |

---

## 2.5  Stack & Subroutine Parameters

6502 stack: 256 bytes at `$0100-$01FF`, manipulated with `PHA/PLA`, `PHP/PLP`, `TSX`, and `TXS`.

Rules:

- `JSR` pushes the return address minus one; any inline-parameter trick must adjust that address and put a valid return address back before `RTS`.
- A bare `PLA/PLA` pair that consumes the return address is **not** a complete inline-parameter routine; if you do that, you must also provide an alternate way back to the caller.
- If you need self-relative data, a stack-relative `TSX`/indexed read pattern is often safer than destroying the return address.

---

*Content fully self-contained. All key facts are present in this file.*
