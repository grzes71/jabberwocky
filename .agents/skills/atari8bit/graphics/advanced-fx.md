---
name: atari8bit-advanced-graphics-effects
description: >-
  Atari advanced graphics effects: GTIA 9/10/11 usage, interlaced picture
  families such as HIP/RIP/TIP, and practical timing rules for DLI-driven
  display effects.
---

# Advanced Graphics Effects (HIP, RIP, TIP, GTIA 9++)

Advanced Atari picture effects are built from ordinary ANTIC + GTIA features:

- ANTIC mode F screen memory
- GTIA modes 9/10/11 via `PRIOR`
- DLI-driven register changes
- sometimes frame interlace or palette alternation

They are **software techniques**, not extra built-in hardware modes.

## GTIA 9/10/11: the reliable baseline

Before using any advanced effect, know the three real GTIA colour modes:

| Mode | `PRIOR` bits 7-6 | BASIC | Summary |
|---|---|---:|---|
| GTIA 9 | `01` / `$40` | 9 | 16 luminances of the hue in `COLBK` |
| GTIA 10 | `10` / `$80` | 10 | 9 colour-register selections on the playfield |
| GTIA 11 | `11` / `$C0` | 11 | 15 hues at one luminance from `COLBK`, plus background |

All three usually use ANTIC mode F memory: 40 bytes per scan line, 192 scan
lines, 7,680 bytes at normal width.

## HIP / RIP / TIP

HIP, RIP, and TIP are scene names for interlaced picture formats. They are not
described by one universal DLI kernel or one universal palette table.

What is safe to say:

- they rely on rapid alternation of GTIA colour interpretations and/or palette values
- many implementations use two display lists or two frame states
- they are sensitive to exact scan-line timing
- they can flicker, especially on LCDs or badly tuned captures

What is **not** safe to assume from a generic reference:

- one fixed scan-line sequence
- one fixed palette packing scheme
- one fixed DLI routine that works for every converter or picture format

So if you are implementing HIP/RIP/TIP, take the line order, palette layout,
and DLI sequence from a converter-specific or code-specific source.

## “GTIA 9++” and similar demo tricks

Some demos abuse `VSCROL`, display-list structure, or other cycle-exact timing
to change the apparent aspect ratio or scan-line reuse of GTIA pictures.
Those tricks are real as **specific kernels**, but they are not a standard
documented GTIA operating mode.

Treat them as:

- implementation-specific
- timing-critical
- something to copy from proven code, not from a generic formula

## Practical Rules

- In GTIA 9/10/11, `HSCROL` should move in **even values only**.
- Use OS shadows in VBI-driven code; write hardware registers directly only when
  you need a same-frame change in a DLI.
- PMG overlays remain available and are often used for cursors, UI, or extra colours.
- Test on real GTIA timing or a cycle-accurate emulator such as Altirra before
  trusting any cycle-counted picture kernel.
