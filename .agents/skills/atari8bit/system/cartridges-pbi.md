---
name: atari8bit-cartridges-pbi
description: >-
  Atari 8-bit cartridge windows, cartridge banking, PBI expansion devices,
  internal devices, and reverse-engineering notes.
---

# Cartridges, PBI, and Internal Devices

> **When to load:** The task involves ROM carts, banked carts, PBI devices, IDE/SIDE-like hardware, internal clocks, or device-space reversing.
> **Source note:** This file is self-contained.

## Cartridge Basics

Atari 8-bit cartridges map ROM into fixed CPU address windows. Reverse them as banked memory devices, not as ordinary XEX files.

Common windows:

| Window | Signal / use |
|---|---|
| `$8000-$9FFF` | Lower 8K cartridge window (`RD4`; the right slot on the 800, otherwise the lower half of a 16K cart) |
| `$A000-$BFFF` | Upper 8K cartridge window (`RD5`; the left slot, present on all models) |
| `$BFFA-$BFFF` | Cartridge vectors / signature area in many formats |
| `$D500-$D5FF` | `CCTL` cartridge control space, often used for bank switching or cart-side registers |

`CARTCS` (`$BFFA`) is the two-byte cartridge cold-start address the OS executes; `CARTAD` (`$BFFE`) is the two-byte cartridge start vector used during initialization. `RD4` and `RD5` are the strobes for the lower and upper 8K windows.

On the 800, the left physical slot corresponds to the `$A000-$BFFF` window and the right slot to `$8000-$9FFF`; the 400 has only the left slot. XL/XE-class machines expose a single edge connector but still use the same two logical 8K windows.

### CCTL false-read hazard

Many bank-switched carts decode only the address in `$D500-$D5FF`, not the data value or write strobes. That means **reads can switch banks too**.

Practical rule: avoid indexed accesses or stray DMA through `CCTL` / device-control pages unless the cart documentation explicitly says the registers are write-only.

### Reset and startup behavior

The computer RESET key does not guarantee that cartridge banking hardware returns to its power-on state. A banked cart should keep valid startup code in every possible power-up bank, or vector quickly from every bank to a known startup bank.

Reversing workflow:

1. Identify ROM size and visible initial bank.
2. Locate cartridge vectors / signature bytes.
3. Watch reads or writes to `$D5xx` and any documented control range.
4. Build a bank-switch table before linear disassembly.
5. Treat code reached after a bank change as a different address-space state.

## Banked Cartridge Rules

- A CPU address is not enough to identify code; record `(bank, address)`.
- Bank registers can be write-only; infer current bank from the last access.
- Interrupt handlers must live in always-visible ROM/RAM or restore the expected bank before executing.
- Self-modifying code cannot patch ROM, but can copy routines to RAM and patch the RAM copy.
- Some carts turn themselves off by dropping `RD4`/`RD5`; after an off command, execution may continue from RAM or OS ROM.

Common cartridge families useful for reversing:

| Family | Bank-control rule |
|---|---|
| OSS 16K | Uses a fixed 4K bank at `$B000-$BFFF` and a selectable 4K bank at `$A000-$AFFF`; bank choice is encoded by the accessed control address |
| SpartaDOS X / Express / Diamond | Bank 8K pages into `$A000-$BFFF`; low control addresses select banks and higher ones typically disable the cart |
| XEGS | Larger XEGS carts keep the last 8K bank fixed at `$A000-$BFFF` and switch 8K banks into `$8000-$9FFF` through `CCTL` |
| Atarimax / MaxFlash | Use `CCTL` banking; exact address decode differs between 1 Mbit and 8 Mbit designs |
| MyIDE / MyIDE-II | Combine flash banking with ATA register windows in the `$D500` page |
| R-Time 8 | Pass-through cart with RTC hardware; reads are often enough to access the clock |

## PBI Overview

The Parallel Bus Interface exposes expansion hardware on XL-class systems. PBI devices can add ROM handlers, disk interfaces, memory, clocks, or other peripherals.

PBI reserves `$D1xx`, `$D6xx`, and `$D7xx` for the active device. `$D1FF` is conventionally used as the device-select / interrupt-status register:

- Writing one bit selects the corresponding device; writing `$00` deselects devices.
- Reading reports interrupt requests from devices that implement the status convention.
- Real hardware may partially decode the register or overload bits with device-specific behavior.

An active PBI device can overlay ROM into `$D800-$DFFF` by asserting Math Pack Disable (`MPD`). PBI overlays do not replace GTIA/POKEY/PIA/ANTIC I/O space.

Key hardware behavior:

| Signal | Meaning for software/reversing |
|---|---|
| `EXTENB` | External decoder enable for PBI-legal address ranges |
| `EXTSEL` | Selected device owns the current addressed range |
| `MPD` | Lets the device replace the Math Pack area at `$D800-$DFFF` |
| `RDY` | Slow device can stretch a CPU cycle |
| `IRQ` | PBI devices can interrupt the CPU |
| `AUDIO IN` | Expansion audio can be mixed into the host audio path |

The 600XL and 800XL expose the full external PBI; the 1064 memory expansion is a PBI device for the 600XL. XE machines (65XE/130XE/800XE) typically expose the reduced ECI connector plus the cartridge connector instead of a full PBI.

Agent rules:

- If code scans device IDs or handler tables, treat it as expansion discovery.
- If code patches CIO/SIO behavior after reset, check for PBI-resident handlers.
- If a program depends on PBI hardware, document fallback behavior or requirement.

### Common PBI/Internal Devices

| Device | Key software-visible facts |
|---|---|
| ICD MIO | PBI mass-storage / I/O interface; occupies PBI device space when selected |
| Covox-style DAC | Usually write-only audio at an implementation-specific decode range such as `$D6xx/$D7xx` |
| Ultimate1MB | Internal expansion with extra RAM and selectable ROM images; treat flash-mapped regions as shared state |
| VBXE | Often uses `$D6xx/$D7xx` windows and has its own detection/initialization rules |

## Internal Devices and Clocks

Internal or pseudo-internal devices can appear through OS vectors, PBI, or SIO commands.

Examples in this corpus:

| Device | Skill location |
|---|---|
| APE-Time RTC | `exotics/sophia-rapidus.md` |
| VBXE | `exotics/vbxe.md` |
| Sophia | `exotics/sophia-rapidus.md` |
| XEP80 and accessories | `system/input.md` |

## Reverse-Engineering Notes

- Hardware control ranges often decode incompletely and mirror across address ranges.
- Some devices require timing gaps after commands; do not collapse polling loops unless the hardware docs say it is safe.
- For emulation-targeted code, note whether Altirra supports the device and whether real hardware timing has been tested.
