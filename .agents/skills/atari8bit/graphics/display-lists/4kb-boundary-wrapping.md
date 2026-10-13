# 4KB Memory Boundary Wrapping & LMS Segment Alignment

## §7  ANTIC Playfield Counter Limit & 4KB Memory Boundary Wrapping

ANTIC's **playfield-memory scan counter** increments only within the current
4 KB block. If screen data for a bitmap mode crosses a 4 KB boundary and you do
not reload the address with an LMS instruction, ANTIC wraps to the start of the
same 4 KB block instead of continuing into the next one.

This is a **playfield-data** rule, not a display-list-pointer rule.

### Root Cause Mechanics

1. **4 KB wrap:** when sequential playfield fetches reach `$xFFF`, the next
   byte comes from `$x000` unless an LMS reloads the counter.
2. **Mode math for 40 bytes/scan line:**
   - ANTIC **D**, **E**, and **F** all fetch **40 bytes** per normal-width scan line.
   - `4096 / 40 = 102` full lines with **16 bytes left over**.
   - Therefore line 102 (the 103rd scan line, counting from 0) would straddle
     the 4 KB boundary if you let the counter run straight through.

---

## The Mid-Scanline Wrapping Gotcha

A common mistake is reloading to `IMAGE_BUFFER + 4080` (for example `$4FF0`
when `IMAGE_BUFFER = $4000`) and expecting line 102 to continue into `$5000`.
It will not.

- `$4FF0` leaves only **16 bytes** before `$5000`.
- A 40-byte scan line then fetches 16 bytes from `$4FF0..$4FFF` and wraps the
  remaining 24 bytes to `$4000..$4017`.
- Visually, the scan line splits horizontally because the right end of one row
  is followed by the left end of the 4 KB block.

---

## 4KB Alignment & Padding Solution

1. **Pad each 4 KB source block** in memory to a full 4096 bytes.
2. **Reload with LMS at the next 4 KB boundary**, e.g. `$5000`, before the
   first line that would cross.

### MADS Assembly Example (192 lines)

```mads
DLIST_PREVIEW
    ; --- Upper Margin ---
    dta $70, $70, $70               ; 24 blank lines

    ; --- Segment 1: Lines 0..101 (102 lines = 4080 bytes) ---
    dta $4E, a(IMAGE_BUFFER + 0)    ; LMS Mode E: start of VRAM ($4000)
    .rept 101
    dta $0E                         ; Mode E scan lines
    .endr

    ; --- Segment 2: Lines 102..191 (90 lines = 3600 bytes) ---
    dta $4E, a(IMAGE_BUFFER + 4096) ; LMS Mode E: reload at $5000
    .rept 89
    dta $0E
    .endr

    ; --- Jump and Wait for Vertical Blank ---
    dta $41, a(DLIST_PREVIEW)
```

For a **190-line** screen, the second segment would be 88 lines instead of 90.

---

## Dynamic 4KB Segment Generator (Python Implementation)

```python
def build_dlist(
    mode: str,
    height: int = 192,
    width: int = 160,
    screen_base_address: int = 0x4000,
    pad_4kb: bool = True,
) -> bytearray:
    mode_byte = 0x0E if mode == "E" else (0x0F if mode == "F" else 0x0D)
    lms_byte = mode_byte | 0x40

    bits_per_pixel = 1 if mode == "F" else 2
    bytes_per_line = (width * bits_per_pixel) // 8
    max_lines_per_segment = 4096 // bytes_per_line  # 102 lines for 40 B/line

    dlist = bytearray([0x70, 0x70, 0x70])

    remaining_lines = height
    current_byte_offset = 0

    while remaining_lines > 0:
        lines_in_segment = min(remaining_lines, max_lines_per_segment)
        segment_bytes = lines_in_segment * bytes_per_line

        target_addr = screen_base_address + current_byte_offset
        dlist.extend([lms_byte, target_addr & 0xFF, (target_addr >> 8) & 0xFF])

        if lines_in_segment > 1:
            dlist.extend([mode_byte] * (lines_in_segment - 1))

        if pad_4kb and remaining_lines > lines_in_segment:
            current_byte_offset += 4096
        else:
            current_byte_offset += segment_bytes

        remaining_lines -= lines_in_segment

    dlist.extend([0x41, screen_base_address & 0xFF, (screen_base_address >> 8) & 0xFF])
    return dlist
```

---

## Quick Reference Summary

| Parameter | Mode D | Mode E | Mode F |
|---|---|---|---|
| Resolution | 160×96 | 160×192 | 320×192 |
| Bits/pixel | 2 | 2 | 1 |
| Bytes / line | 40 | 40 | 40 |
| Max full lines / 4 KB | 102 | 102 | 102 |
| 192-line segments | 1 | 102 + 90 | 102 + 90 |
