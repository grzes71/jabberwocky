# Dma Timing

## 3.1  ANTIC Architecture, DMA & Timing

### Clock tree

| item | NTSC | PAL |
|---|---|---|
| Master crystal | 14.318 18 MHz | 14.187 57 MHz |
| Machine clock (CPU) | 14.318 18 ÷ 8 = **1.789 773 MHz** | 14.187 57 ÷ 8 = **1.773 447 MHz** |
| Color clock | 3.579 545 MHz | 4.433 618 MHz ÷ 2 |
| Cycles / scan line | **114** | **114** |
| Scan lines / frame | 262 (NTSC) | 312 (PAL) |
| Frame rate | 59.922 71 Hz | 49.860 74 Hz |

### Playfield widths (`DMACTL` bits 0–1)

| Width | Color clocks | Bytes/line (text or normal-width bitmap fetch) | Use |
|---|---|---|---|
| Narrow | 128 | 32 | Saves DMA |
| Normal | 160 | 40 | Default |
| Wide | 192 | 48 | Overscan / wide playfield |

### DMA overview

ANTIC steals 6502 bus cycles for several jobs:

- display-list fetches,
- screen-memory fetches,
- character-glyph fetches in character modes,
- player/missile DMA when enabled,
- DRAM refresh.

Practical consequences:

- Character modes are heaviest on the **first scan line of a mode line**, when
  ANTIC must fetch both screen codes and character data.
- Enabling **HSCROL** makes ANTIC fetch one playfield width larger for narrow
  and normal screens to provide the scroll buffer.
- Enabling **player DMA** also consumes the missile-DMA time slot, even if you
  are not using missiles visibly.
- Cycle budgets vary by mode, width, scrolling, and PMG DMA, so for exact
  split timing use `WSYNC` and test on real hardware or a cycle-accurate
  emulator.

### Memory refresh

Classic ANTIC references document **9 DRAM refresh cycles per scan line**.
These refresh slots are part of ANTIC's normal DMA budget and therefore reduce
CPU time available on each line.

### Bus and video landmarks

| Event | Meaning |
|---|---|
| Scan line length | 114 CPU cycles = 228 color clocks |
| `HSCROL` unit | 1 color clock |
| Visible playfield widths | 128 / 160 / 192 color clocks |
| `WSYNC` | CPU pauses until the end of the current scan line |

Display-list instructions cost one DMA fetch per byte. `LMS` and `JMP/JVB`
instructions therefore consume three display-list bytes instead of one.
