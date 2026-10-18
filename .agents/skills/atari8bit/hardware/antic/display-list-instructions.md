# Display List Instructions

## 3.2  Display List Instructions

A display list is a stream of 1-byte or 3-byte instructions. The current
pointer lives in `DLISTL/DLISTH` at `$D402/$D403`.

### Instruction encoding

There are three instruction families:

1. **Blank lines** — bits 6–4 encode the blank-line count minus 1,
   bit 7 is optional DLI, bits 3–0 are zero.
2. **Jump instructions** — `$01` = JMP, `$41` = JVB; both are followed by
   a 16-bit address (low byte first).
3. **Mode lines** — low nibble = ANTIC mode 2–F; add modifier bits:
   `$10` = HSCROL, `$20` = VSCROL, `$40` = LMS, `$80` = DLI.

### Common instruction bytes

| Byte | Meaning |
|---|---|
| `$70` | 8 blank scan lines |
| `$F0` | 8 blank scan lines with DLI on the last blank line |
| `$42` | Mode 2 + LMS |
| `$4E` | Mode E + LMS |
| `$74` | Mode 4 + HSCROL + VSCROL + LMS |
| `$8F` | Mode F + DLI |
| `$01` | Jump |
| `$41` | Jump and wait for vertical blank |

### Notes

- **Blank instructions do not use LMS/HSCROL/VSCROL bits.** In blank-line
  opcodes, bits 6–4 are the blank-line count.
- **DLI fires on the last scan line** of a DLI-tagged blank or mode-line
  instruction.
- **LMS** loads the playfield-memory scan counter. Use it at the top of a
  region and before any 4 KB playfield-memory wrap.
- **JVB** is the normal end-of-list instruction: ANTIC waits for vertical
  blank and restarts execution at the supplied address on the next frame.
- Many Atari references recommend keeping the display list within one **1 KB block** or jumping before the boundary if you are close to crossing it.

### Playfield modes at a glance

| Mode | Description |
|---|---|
| 2 | 40-column text, 8 scan lines per row (40 bytes/line) |
| 3 | 40-column text with descenders, 10 scan lines per row |
| 4 | 40-column 4-color text, 8 scan lines per row |
| 5 | 40-column 4-color text, double height (16 scan lines per row) |
| 6 | 20-column text, character-selected foreground color, 8 scan lines per row |
| 7 | 20-column text, double height (16 scan lines per row) |
| 8 | 40-column 4-color map, 8 scan lines per row (10 bytes/line) |
| 9 | 80-pixel 2-color map, 4 scan lines per row |
| A | 40-pixel 4-color map, 4 scan lines per row |
| B | 80-pixel 2-color map, 2 scan lines per row |
| C | 160-pixel 2-color map, 1 scan line per row |
| D | 160-pixel 4-color bitmap, 2 scan lines per row |
| E | 160-pixel 4-color bitmap, 1 scan line per row |
| F | 320-pixel 2-color high-resolution bitmap, 1 scan line per row |

