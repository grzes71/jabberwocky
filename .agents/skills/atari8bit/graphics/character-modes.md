---
name: atari8bit-character-modes
description: >-
  Atari ANTIC character (text) modes 2-7: mode geometry, glyph formats,
  character-set memory, CHBASE/CHACTL, mode 3 descenders, multicolor modes 4/5,
  DLI charset swaps, and soft-pixel plotting via character cells.
---

# Character Modes

> Sources: Wikipedia "ANTIC" (registers CHACTL/CHBASE, Glyph Rendering),
> De Re Atari ch. 2-3, Altirra Hardware Reference Manual (ANTIC chapter).

## Overview

ANTIC character modes are **2, 3, 4, 5, 6, 7** (there are no character modes
0, 1 or F — `$0`/`$1` are blank-line/jump instructions, `$F` is a bitmap mode).
Screen memory holds one **character code byte per cell**; ANTIC uses that code
to fetch glyph rows from the character set pointed to by `CHBASE`.

Every glyph is **8 bytes** (one byte per glyph row, row 0 first) regardless of
mode. Glyph address = `CHBASE*256 + code*8` (code masked to 7 bits for modes
2-5, 6 bits for modes 6/7).

## Mode Table

Bytes per mode line = characters per line (one screen byte per cell).
Widths given as narrow / normal / wide playfield (`DMACTL` bits 0-1).

| ANTIC | OS GR. | Chars (bytes) per line | Scan lines / mode line | Glyph pixel (color clocks × scan lines) | Bits / glyph pixel | Cell (pixels) | Chars in set | Set size / alignment |
|-------|--------|------------------------|------------------------|------------------------------------------|--------------------|---------------|--------------|----------------------|
| 2     | 0      | 32 / 40 / 48           | 8                      | ½ × 1                                    | 1                  | 8 × 8         | 128          | 1 KB / 1 KB          |
| 3     | —      | 32 / 40 / 48           | 10                     | ½ × 1                                    | 1                  | 8 × 10        | 128          | 1 KB / 1 KB          |
| 4     | 12 (XL)| 32 / 40 / 48           | 8                      | 1 × 1                                    | 2                  | 4 × 8         | 128          | 1 KB / 1 KB          |
| 5     | 13 (XL)| 32 / 40 / 48           | 16                     | 1 × 2                                    | 2                  | 4 × 8         | 128          | 1 KB / 1 KB          |
| 6     | 1      | 16 / 20 / 24           | 8                      | 1 × 1                                    | 1                  | 8 × 8         | 64           | 512 B / 512 B        |
| 7     | 2      | 16 / 20 / 24           | 16                     | 1 × 2                                    | 1                  | 8 × 8         | 64           | 512 B / 512 B        |

Derived (normal width): mode 2 = 320 hi-res pixels/line, mode 4 = 160
pixels/line (40 chars × 4), mode 6 = 160 pixels/line (20 chars × 8).
A full 24-row mode 2 or mode 4 screen = 960 bytes of screen memory.
Modes 5 and 7 show each glyph row on two scan lines (double height).

## Glyph Rendering

### Mode 2 — Standard (hi-res, 1 bpp)
- Bit = 1: pixel shows **luminance of COLPF1** on hue of COLPF2.
- Bit = 0: background **COLPF2**. COLBK is only the border.
- Pixel = ½ color clock → NTSC/PAL artifacting on single-pixel columns.
- Code bit 7 = "inverse" character, handled by `CHACTL` (see below).

### Mode 3 — Descenders (10 scan lines)
Same colors as mode 2; glyph still 8 bytes, mode line is 10 scan lines:

| Codes (bits 0-6) | Scan lines 0-1 | Scan lines 2-7 | Scan lines 8-9 |
|------------------|----------------|----------------|----------------|
| `$00`–`$5F`      | glyph rows 0-1 | glyph rows 2-7 | blank          |
| `$60`–`$7F`      | blank          | glyph rows 2-7 | glyph rows 0-1 |

So for lowercase descenders, store the descender part in glyph bytes 0-1.

### Modes 4/5 — Multicolor (2 bpp)
Each bit pair of the glyph byte = one pixel, 1 color clock wide
(bits 7-6 = leftmost pixel). Up to 4 colors per cell, 5 per screen:

| Bit pair | Code bit 7 = 0 | Code bit 7 = 1 |
|----------|----------------|----------------|
| `00`     | COLBK          | COLBK          |
| `01`     | COLPF0         | COLPF0         |
| `10`     | COLPF1         | COLPF1         |
| `11`     | COLPF2         | **COLPF3**     |

CHACTL inverse/blank bits have **no effect** in modes 4/5.

### Modes 6/7 — Single color (1 bpp, 64 chars)
Code bits 0-5 select the glyph; bits 7-6 select the foreground color.
Bit = 0 → COLBK.

| Code bits 7-6 | Range       | Foreground |
|---------------|-------------|------------|
| `00`          | `$00`–`$3F` | COLPF0     |
| `01`          | `$40`–`$7F` | COLPF1     |
| `10`          | `$80`–`$BF` | COLPF2     |
| `11`          | `$C0`–`$FF` | COLPF3     |

## CHBASE — Character Set Base

| Register | Address | Access | OS shadow     |
|----------|---------|--------|---------------|
| `CHBASE` | `$D409` | write  | `CHBAS $02F4` |

- **Single byte** = high byte (page) of the character set address.
- Modes 2-5: set must be 1 KB aligned (low 2 bits ignored).
  Modes 6/7: 512 B aligned (bit 0 ignored).
- OS default `$E0` → ROM set at `$E000` (GR.1/2 commonly use `$E2` for the
  lowercase/graphics half).
- The OS VBI copies `CHBAS → CHBASE` every frame. With OS running, write the
  shadow; write `CHBASE` directly only in a DLI (it is restored next VBI).
- A custom set must be fully written to RAM before pointing `CHBAS` at it,
  otherwise garbage is displayed for the frames in between.

```asm
        ; copy 1 KB font to FONT (1 KB aligned), then:
        lda #>FONT
        sta CHBAS           ; OS shadow, takes effect next VBI
```

## CHACTL — Character Control

| Register | Address | Access | OS shadow                              |
|----------|---------|--------|----------------------------------------|
| `CHACTL` | `$D401` | write  | `CHACT $02F3` (also listed as `CHART`) |

| Bit | Value | Name    | Effect                                                         |
|-----|-------|---------|----------------------------------------------------------------|
| 0   | `$01` | Blank   | Characters with code bit 7 set are shown as blank             |
| 1   | `$02` | Inverse | Characters with code bit 7 set are shown in inverse video     |
| 2   | `$04` | Reflect | All characters drawn upside down (glyph rows reversed)        |

- OS default = `$02` (inverse on).
- `$03` (blank + inverse) → inverse chars appear as solid inverse blocks.
- Toggling bit 0 or 1 makes every inverse char blink globally (cursor blink).
- Bits 0-1 affect **modes 2 and 3 only**; bit 2 affects all text modes.
- Reflect in mode 3: rows are reversed before the descender remap, so
  lowercase chars look inconsistent (glyph bytes 6-7 land in descender area).
- CHACTL is **not** a write-mode / masking control — CPU writes to screen
  RAM are ordinary stores; ANTIC only reads.

## DLI Character Set Swaps

More than 128 (or 64) glyphs on one screen: change `CHBASE` mid-frame from a
DLI on the mode line *before* the target band.

```asm
dli_font
        pha                 ; 3
        lda #>FONT2         ; 2
        sta WSYNC           ; 4  wait for end of scan line
        sta CHBASE          ; 4  new set from next mode line
        pla                 ; 4
        rti                 ; 6
```

- VBI (OS: from `CHBAS`) restores the top-of-screen set every frame.
- Same technique works for `CHACTL` (e.g. reflected water band).
- See [display-lists.md](display-lists.md) for DLI bit setup and timing.

## Smooth Scrolling

Character modes support `HSCROL` ($D404) / `VSCROL` ($D405) when the
display-list instruction has the HS (`$10`) / VS (`$20`) bit set.
`VSCROL` range is 0..(scan lines per mode line − 1): 0-7 for modes 2/4/6,
0-9 for mode 3, 0-15 for modes 5/7. Coarse scroll by changing LMS addresses.
Details: [scrolling.md](scrolling.md).

## Technique: Soft Pixels via Character Cells

A 2×2 block font gives 80×48 "pixels" on a 40×24 mode 2 screen (or more
colors in mode 4). Define glyphs `0`–`15` so that code bits 0-3 represent
the four quadrants (TL=1, TR=2, BL=4, BR=8). Plot/unplot is then a plain
bit operation on the screen byte:

```asm
        ; A = quadrant mask (1/2/4/8), (ptr),y = cell
        ora (ptr),y         ; set   — use AND #~mask to clear
        sta (ptr),y
```

Generalization: for arbitrary per-cell content, keep a 128-entry glyph pool,
allocate glyphs dynamically, and plot into glyph bytes (soft-sprite engines).
See [software-sprites.md](software-sprites.md).

## Common Pitfalls

- Modes 4/5 screen = 40 bytes/line, not 20; pixels are 4 per char.
- Glyph data for modes 4/5 are bit **pairs**; an 8-pixel-wide 1 bpp font
  drawn in mode 4 looks like garbage.
- ANTIC sees the same memory map as the CPU: a font in RAM under OS ROM
  (`$C000`+) is only visible while PORTB bit 0 = 0 (ROM disabled). In this
  project fonts must stay ≤ `$BFFF` (see AGENTS.md).
- Mode 6/7 sets are 512 B; a 1 KB font pointed at them shows only the first
  half (`$E0` = uppercase/digits, `$E2` = graphics/lowercase).
