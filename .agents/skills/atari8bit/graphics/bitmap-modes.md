---
name: atari8bit-bitmap-modes
description: >-
  Atari ANTIC and GTIA bitmap graphics modes: hires and multicolor screen memory,
  line addressing, plotting, GTIA overlays, and custom display-list layouts.
---

# Bitmap Graphics Modes

## Bitmap Mode Table (ANTIC 8-F)

Common Atari bitmap work is usually done in ANTIC modes E and F, but the full
bitmap family spans ANTIC modes 8-F:

| ANTIC | Typical OS/BASIC mode | Pixels per mode line (normal width) | Scan lines per mode line | Bytes per mode line (normal width) | Bits/pixel | Colors |
|---|---:|---:|---:|---:|---:|---|
| 8 | 3 | 40 | 8 | 10 | 2 | 4 |
| 9 | 4 | 80 | 4 | 10 | 1 | 2 |
| A | 5 | 80 | 4 | 20 | 2 | 4 |
| B | 6 | 160 | 2 | 20 | 1 | 2 |
| C | 14 (XL OS) | 160 | 1 | 20 | 1 | 2 |
| D | 7 | 160 | 2 | 40 | 2 | 4 |
| E | 15 (XL OS) | 160 | 1 | 40 | 2 | 4 |
| F | 8 | 320 | 1 | 40 | 1 | 2 hi-res |

GTIA modes 9/10/11 use the **same 40-byte ANTIC F layout** as mode F; GTIA
changes the colour interpretation, not the memory layout.

For full-height 192-line screens at normal width:

- ANTIC E = `40 × 192 = 7680` bytes
- ANTIC F = `40 × 192 = 7680` bytes
- GTIA 9/10/11 = same as ANTIC F

## Screen Layout and Addressing

For ANTIC E, ANTIC F, and GTIA 9/10/11, screen memory is linear by scan line:

```text
screen_addr = screen_base + y * 40
```

A full ANTIC E/F screen crosses a 4 KB boundary, so a custom display list
normally needs a second LMS near mid-screen.

Precompute line-address tables instead of multiplying by 40 in inner loops:

```asm
line_lo  .byte <(screen+0*40), <(screen+1*40), <(screen+2*40)
line_hi  .byte >(screen+0*40), >(screen+1*40), >(screen+2*40)
```

## Plotting Rules

### ANTIC E / 2 bpp / 160 pixels

Four pixels share one byte:

```text
byte_addr = screen_base + y*40 + (x >> 2)
shift     = 6 - ((x & 3) * 2)
new_byte  = (old_byte & ~(3 << shift)) | ((color & 3) << shift)
```

Setting one pixel therefore requires a **read-modify-write** unless the write
already covers a whole aligned byte.

### ANTIC F / 1 bpp / 320 pixels

Eight pixels share one byte:

```text
byte_addr = screen_base + y*40 + (x >> 3)
mask      = $80 >> (x & 7)
```

- set pixel: `old_byte OR mask`
- clear pixel: `old_byte AND (NOT mask)`

Again, individual-pixel plotting is a read-modify-write operation.

### Byte-oriented fills

Horizontal lines and solid areas are fastest when:

1. left edge byte is masked
2. middle bytes are written as full-byte fills
3. right edge byte is masked

If both endpoints fall in the same byte, combine the masks and do one read-modify-write.

## Colour Behaviour

- ANTIC E uses the normal four playfield colours (`COLBK`, `COLPF0-2`).
- ANTIC F is the half-color-clock hi-res mode:
  - 0 bits use `COLPF2`
  - 1 bits use the hue of `COLPF2` with the luminance of `COLPF1`
  - `COLBK` is the border colour
- On NTSC hardware, ANTIC F can also show artifact colours. On PAL systems it
  is effectively monochrome.

## GTIA Overlays

GTIA modes 9/10/11 reinterpret ANTIC F bytes as 4-bit pixels:

- normal-width visible resolution becomes **80 pixels**
- bytes per scan line stay at **40**
- `HSCROL` should use **even values only**

Player/missile graphics can still be overlaid on bitmap modes; see
`graphics/pm-graphics.md`.

## Custom Heights and Overscan

Standard OS graphics modes are 192 scan lines tall, but ANTIC can display up to
roughly 240 visible scan lines with a custom display list and overscan timing.
Those kernels are timing-sensitive and TV-dependent; copy a known working
routine rather than improvising one from generic formulas.
