# Scroll Timing

## §2.1  VSCROL / HSCROL Update Rules

`VSCROL` and `HSCROL` are most reliable when written in **VBI** or
immediately after `WSYNC` in a DLI.

### VSCROL behaviour

- `VSCROL` is measured in **scan lines**.
- Valid values are `0..height-1` for the current ANTIC mode line.
- A vertical scrolling region is formed by one or more consecutive display-list
  instructions with the **VS** bit set; the first following line without VS is
  the **buffer line**.

For an 8-scan-line mode such as ANTIC 2, 4, or 6:

| VSCROL | First scrolled line shows | Buffer line shows |
|---|---|---|
| 0 | scan lines 0–7 | scan line 0 |
| 1 | scan lines 1–7 | scan lines 0–1 |
| 2 | scan lines 2–7 | scan lines 0–2 |
| 3 | scan lines 3–7 | scan lines 0–3 |
| 7 | scan line 7 | scan lines 0–7 |

**Practical rule:** if a DLI changes `VSCROL`, do `WSYNC` first and then write
`VSCROL` as early as possible on the new scan line.

### HSCROL rules

| Rule | Explanation |
|---|---|
| Only low 4 bits matter | scroll amount is 0–15 color clocks |
| Narrow/normal screens fetch one width larger | ANTIC needs the extra buffer bytes |
| GTIA 9/10/11 should use even values | odd values disturb GTIA pixel pairing |
| Visible-line changes are risky | prefer HBLANK / `WSYNC` updates |
