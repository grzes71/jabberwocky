# Gtia Modes

## §4.5  GTIA Colour Interpretation Modes

GTIA adds three alternate colour interpretations selected by **bits 6-7 of
`PRIOR ($D01B)`**. These are usually used with **ANTIC mode F** screen memory
(40 bytes per scan line, 192 scan lines, 7,680 bytes at normal width), though
the colour interpretations also apply to ANTIC modes 2 and 3.

CTIA-equipped early 400/800 machines do **not** support these three modes.

| `PRIOR` bits 7-6 | Value | BASIC | Meaning |
|---|---:|---:|---|
| `00` | `$00` | — | Normal CTIA/GTIA playfield colour rules |
| `01` | `$40` | 9 | 16 luminances of one hue |
| `10` | `$80` | 10 | 9 colour-register selections on the playfield |
| `11` | `$C0` | 11 | 15 hues at one luminance, plus background |

### GTIA 9 (`PRIOR = $40`, BASIC 9)

- Pixel values are interpreted as **luminance 0-15**
- The **hue comes from `COLBK`**
- Pixels are 2 color clocks wide, so normal-width resolution is **80 pixels**
- Playfield collision detection is **disabled**

This is the standard “16 shades of one hue” mode.

### GTIA 10 (`PRIOR = $80`, BASIC 10)

- Pixel values `0-8` select the nine hardware colour registers
  (`COLPM0-3`, `COLPF0-3`, `COLBK`)
- Higher pixel values alias earlier entries rather than creating new colours
- The visible background/border colour comes from **`COLPM0`**
- Playfield pixels using `COLPF0-3` participate in playfield collision latches;
  pixels using `COLPM0-3` or `COLBK` do not

This is the only GTIA mode that exposes the full set of nine colour registers
on the playfield at once.

### GTIA 11 (`PRIOR = $C0`, BASIC 11)

- Pixel values `1-15` select **hues**
- The shared luminance comes from **`COLBK`**
- The background uses the colour component of `COLBK` with luminance forced to 0
- Playfield collision detection is **disabled**

This is the standard “many hues at one brightness” mode.

### Scrolling and Resolution Notes

- GTIA modes still use ANTIC’s horizontal and vertical scrolling hardware.
- Because GTIA pixels are **2 color clocks wide**, `HSCROL` should be changed
  in **even values only** when using GTIA 9/10/11.
- The playfield is still fetched as ANTIC mode F bytes. GTIA changes only the
  colour interpretation, not the underlying memory layout.

### About HIP / RIP / TIP / “GTIA 9++”

HIP, RIP, TIP, and related scene-picture names are **software formats and
display kernels**, not built-in GTIA modes. They rely on frame interlace,
scan-line `PRIOR` changes, palette changes, or other cycle-exact tricks.

Because their exact line order, palette packing, and DLI timing vary by
converter and implementation, this file intentionally avoids prescribing a
single “universal” palette table or DLI routine for them. Use known working
code or a converter-specific reference when implementing one of those formats.
