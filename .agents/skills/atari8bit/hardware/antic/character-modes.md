# Character Modes

## 3.4  Character Modes (ANTIC 2–7)

| Mode | Scan lines | Characters/line | Character memory | Colors |
|---|---|---|---|---|
| 2 | 8 | 40 | 1 KB @ 1 KB boundary | 2 |
| 3 | 10 | 40 | 1 KB @ 1 KB boundary | 2 (descenders) |
| 4 | 8 | 40 | 1 KB @ 1 KB boundary | 4+1 |
| 5 | 16 | 40 | 1 KB @ 1 KB boundary | 4+1 |
| 6 | 8 | 20 | 512 B @ 512 B boundary | 5 |
| 7 | 16 | 20 | 512 B @ 512 B boundary | 5 |

- **Modes 2/3** use 128 characters. Bit 7 of the screen code is handled by
  `CHACTL` (inverse/blank).
- **Modes 4/5** are 2-bits-per-pixel character modes. Bit pairs map to
  `COLBK`, `COLPF0`, `COLPF1`, and `COLPF2`; when screen-code bit 7 is set,
  the `11` pair uses `COLPF3` instead of `COLPF2`.
- **Modes 6/7** use 64 characters. Screen-code bits 7–6 select foreground
  color `COLPF0`–`COLPF3`; bit 0 in the glyph data is background `COLBK`.

### CHBASE

| Register | Address | Access | OS shadow |
|---|---|---|---|
| `CHBASE` | `$D409` | write | `CHBAS $02F4` |

- Modes 2–5 require a **1 KB-aligned** character set.
- Modes 6/7 require a **512 B-aligned** character set.
- With the OS running, write `CHBAS`; the VBI copies it to `CHBASE`.

### CHACTL

| Register | Address | Access | OS shadow |
|---|---|---|---|
| `CHACTL` | `$D401` | write | `CHACT $02F3` (also listed as `CHART`) |

| Bit | Value | Effect |
|---|---|---|
| 0 | `$01` | Characters with code bit 7 set display as blanks |
| 1 | `$02` | Characters with code bit 7 set display in inverse video |
| 2 | `$04` | All character glyphs are vertically reflected |

- Bits 0–1 affect **modes 2 and 3 only**.
- Bit 2 affects **all character modes**.

### DLI charset swaps

A DLI on the mode line before a band can change `CHBASE` for the next band.
Write the hardware register inside the DLI; if the OS is running, the next VBI
restores the top-of-screen value from `CHBAS`.
