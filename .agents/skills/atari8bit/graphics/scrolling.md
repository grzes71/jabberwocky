---
name: atari8bit-scrolling
description: >-
  Atari hardware scrolling: HSCROL/VSCROL, display-list HS/VS bits, coarse+fine
  scroll patterns, bitmap/character-mode ranges, and DLI timing notes.
---

# Scrolling

## Quick-Lookup

| Need | See |
|---|---|
| Registers and DL bits | §1 |
| Horizontal fine scroll | §2 |
| Vertical fine scroll | §3 |
| Useful VSCROL ranges by mode | §4 |
| Coarse+fine scroll pattern | §5 |
| DLI timing notes | §6 |

## §1 Registers and Display-List Bits

- `HSCROL ($D404)` = horizontal fine scroll, **0-15 color clocks**
- `VSCROL ($D405)` = vertical fine scroll, **0-15 scan lines**
- Display-list **bit 4** enables horizontal scrolling on that mode line
- Display-list **bit 5** enables vertical scrolling on that mode line

There are **no OS shadow registers** for `HSCROL` or `VSCROL`; write the
hardware registers directly.

## §2 Horizontal Fine Scroll

When HSCROL is enabled for a line, ANTIC fetches one wider playfield buffer:

- narrow display fetches enough data for normal width
- normal display fetches enough data for wide width

`HSCROL` then selects which 0-15 color clocks from that buffer appear at the
left edge of the screen.

Important consequences:

- `HSCROL` counts **color clocks**, not logical pixels
- ANTIC mode F therefore scrolls in **2 hi-res pixels per step**
- GTIA 9/10/11 should use **even HSCROL values only**, because their pixels are
  2 color clocks wide

As `HSCROL` increases, the display contents appear to move **right**; to keep a
continuous scroll, you also update the coarse screen address when the fine
scroll wraps.

## §3 Vertical Fine Scroll

Vertical fine scrolling works over a **region**:

1. one or more consecutive display-list instructions with the VS bit set
2. followed by one instruction with VS clear, which acts as the **buffer line**

If `VSCROL = n`:

- the first scrolled mode line begins display at scan line `n`
- middle scrolled lines display normally
- the first non-VS line after the region contributes only scan lines `0..n`

So the buffer line is part of the mechanism, not just padding.

## §4 Useful VSCROL Ranges by Mode

The useful VSCROL range is always `0 .. (scan lines per mode line - 1)`.

| Modes | Scan lines per mode line | Useful `VSCROL` values |
|---|---:|---|
| 2, 4, 6, 8 | 8 | `0-7` |
| 3 | 10 | `0-9` |
| 5, 7 | 16 | `0-15` |
| 9, A | 4 | `0-3` |
| B, D | 2 | `0-1` |
| C, E, F | 1 | only `0` |

Modes C, E, and F have one scan line per mode line, so they do not provide a
useful vertical fine-scroll range by themselves.

## §5 Coarse + Fine Scroll Pattern

### Horizontal

Pick one direction convention and keep the fine and coarse steps consistent:

1. change `HSCROL` by one step
2. when it wraps past the useful range, reset it and do the next coarse step
3. reverse both operations for the opposite direction

### Vertical

In an 8-scan-line mode:

1. change `VSCROL`
2. when it wraps, advance or rewind the coarse row pointer / LMS address
3. update the buffer line with the new incoming row

For ANTIC E/F full screens, remember that a 7,680-byte display crosses a 4 KB
boundary, so a custom display list usually needs a second LMS near mid-screen.

## §6 DLI Timing Notes

- Use `WSYNC` when a scroll-register change must land cleanly on the next scan line.
- DLI routines should save/restore registers and stay short.
- If the OS is active, update `SDLSTL/SDLSTH` or other shadows in VBI-driven
  setup code; `HSCROL`/`VSCROL` themselves are direct hardware writes.
- For complex kernels, especially ones mixing scroll and colour changes, verify
  timing in Altirra or on real hardware.
