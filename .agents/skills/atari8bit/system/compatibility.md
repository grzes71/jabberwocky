---
name: atari8bit-compatibility
description: >-
  Atari 8-bit compatibility matrix: 400/800 vs XL/XE, PAL/NTSC, RAM
  expansions, CPUs, CTIA/GTIA, stereo POKEY, VBXE, Sophia, Rapidus.
---

# Compatibility and Detection

> **When to load:** Code must run across Atari 400/800/XL/XE, PAL/NTSC, RAM sizes, or optional upgrades.
> **Source note:** This file is self-contained; use its internal tables and cross-references for compatibility work.

## Quick Matrix

| Feature | 400/800 | XL/XE | Agent risk |
|---|---|---|---|
| RESET key | NMI through ANTIC (`NMIST` bit 5) | Hardware reset | Reset-survival code differs |
| Joystick ports | Four ports on many models | Two ports | Paddle/port assumptions differ |
| PORTB banking | Joystick ports 3/4 role | ROM/RAM banking on XL/XE | Do not use XL/XE banking on 400/800 |
| BASIC ROM | Cartridge / model dependent | Usually internal ROM under PORTB control | Preserve BASIC state if returning to OS |
| Self-test ROM | Not XL/XE-style | PORTB-controlled | Preserve self-test state unless you own the machine |
| ANTIC/GTIA timing | Same family, revision differences | Same family, revision differences | Raster kernels need real target testing |

## PAL/NTSC

- ANTIC determines frame geometry: NTSC systems are about 262 scan lines / 60 Hz; PAL systems about 312 scan lines / 50 Hz.
- On GTIA machines, the preferred software test is the `PAL` register at `$D014`: test bits 1-3 with mask `$0E` (zero means PAL, nonzero means NTSC).
- Early CTIA-only systems do not provide that GTIA PAL-status register; there you must time a frame instead.
- Avoid equality-only waits on `VCOUNT`; use wrap-aware timing or the PAL register so PAL code does not lock on NTSC and vice versa.

## RAM and Banking

| Type | Notes |
|---|---|
| 48K/64K base | Most cross-machine code should assume no extended RAM unless detected |
| 130XE | Four 16K banks selected by `PORTB` bits 2-3; bits 4/5 control CPU and ANTIC access to the `$4000-$7FFF` window |
| RAMBO / Newell | Extends 130XE-style banking with more `PORTB` bits; high-bank encodings are board-specific |
| Compy Shop / COMPY | Similar windowing, but bank encodings differ from RAMBO and often preserve separate CPU/ANTIC mapping |
| 576K / 1088K boards | Reuse additional `PORTB` bits; never assume one universal bit layout across vendors |

Rules:

- Save original `PORTB` before bank switching.
- Preserve OS/BASIC/self-test bits unless intentionally disabling ROM.
- Do not probe extended RAM destructively while DOS or SpartaDOS X owns banks.

## CPU

| CPU | What changes |
|---|---|
| 6502 | Baseline target |
| 65C02 | Adds instructions and fixes some NMOS quirks |
| 65C816 | Native/emulation mode, 16-bit registers, 24-bit addressing |
| Rapidus | Accelerator context; timing-sensitive code needs conservative assumptions |

Use CPU-specific opcodes only after detection or when the target explicitly requires that CPU. Detection of 65C02/65C816/Rapidus-class upgrades is hardware- and firmware-specific; do not rely on undocumented "transparent opcode" probes unless the target platform explicitly documents them.

## Video and Audio Upgrades

| Upgrade | Detection/use |
|---|---|
| CTIA/GTIA | GTIA graphics modes require GTIA; old CTIA machines do not support them |
| Stereo POKEY | Address map and probe method are expansion-specific; use the expansion's documented detection routine |
| VBXE | Probe only through documented VBXE registers; see `exotics/vbxe.md` |
| Sophia | Use Sophia-specific detection rules; see `exotics/sophia-rapidus.md` |

If an effect requires an upgrade, code should either fail cleanly, fall back to stock hardware, or state the requirement in the binary/demo notes.

## Compatibility Checklist

Before generating final code, state:

- target family: 400/800, XL/XE, or both;
- TV timing: PAL, NTSC, or adaptive;
- required RAM and bank scheme;
- required CPU;
- required video/audio upgrades;
- whether OS ROM remains enabled;
- whether DOS/SDX must survive.
