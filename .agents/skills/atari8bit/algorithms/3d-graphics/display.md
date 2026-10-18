# Display and engine

> **Load when:** you need to *drive the screen* for shaded 3D and wire the
> render steps into a working loop. Pairs with `hardware/gtia.md` and
> `hardware/antic.md` for register-level detail.

## 1. The right display mode: GTIA luminance/colour modes

ANTIC's hi-res mode (mode `$F`, 1 bit/pixel) is the base. Setting the top
two bits of `PRIOR` ($D01B; OS shadow `GPRIOR` $026F) makes GTIA
**reinterpret each byte as two 4-bit pixels**, giving three modes:

| PRIOR bits 7–6 | Value | GTIA mode | Each 4-bit pixel is… |
|---|---|---|---|
| 01 | `$40` | 9  | a **luminance 0–15** (one hue, from `COLBK`) |
| 10 | `$80` | 10 | an **index 0–8** into 9 colour registers |
| 11 | `$C0` | 11 | a **hue 0–15** (one luminance) |

Pixel layout: 2 pixels per byte (high nibble = left, low = right).

**Why these are the modes for shaded 3D:**

- **Mode 9** gives 16 real luminance levels of a single hue — exactly what
  Gouraud/flat shading wants. Write the shade value straight into the
  nibble; no dithering. Choose the hue with `COLBK`, and change it per
  screen band with a DLI for multi-hue looks.
- **Mode 10** gives 9 colours (registers `PCOLR0..3`, `COLPF0..3`,
  `COLBK`). Load them as a **luminance/colour ramp** and pixel value 0..8
  is a shade; good when you want colour rather than a single hue.
- **Mode 11** is 16 values of one luminance spread across the hue range
  (value 0 is the background) — niche for 3D (hard to shade), useful for
  colourful flat effects.

A byte is two pixels, so a fill writes two pixels at once; partial spans
need nibble read-modify-write (`rasterizer.md`, fill strategy (b)).

## 2. The VSCROL square-pixel trick

GTIA-mode pixels are wide (a byte spans a chunk of the screen) but only
**one scanline tall**, so they look squashed, and a full-height buffer is
large and slow to fill. The fix: make each *data* line display for 2 or 4
scanlines.

Set the **VS** bit (`$20`) on the mode lines and re-write the vertical
scroll register `VSCROL` ($D405) from a DLI. With VS set, a line begins
displaying at scan line `VSCROL`; scrolling farther than the mode's
scan-line height then re-displays the same row's data (ANTIC's documented
"lines of repeated data" behaviour). For a mode F line (1 scan line) the row
covers scan lines `VSCROL..15` then `0`, i.e. `17 − VSCROL` scanlines:
`VSCROL=13` → 4, `VSCROL=15` → 2.

```asm
DLI     pha
        sta WSYNC            ; align to horizontal blank
        lda #13              ; 17-13 = 4 scanlines of the same row
        sta VSCROL           ; (15 -> 2 scanlines)
        pla
        rti
```

Because the offset is applied when a row *starts*, it must be re-written for
every repeated row — one `sta VSCROL` per data line, i.e. one DLI per data
line (~29 cycles of handler body each, plus the interrupt entry). The exact
values are timing-sensitive: check them on real hardware or a cycle-accurate
emulator.

Result: **square pixels** and, at 4 scanlines/pixel, **one quarter** of the
data lines to fill (e.g. 48 data lines cover 192 scanlines). Choose 4
scanlines/pixel for maximum speed (fewer, chunkier pixels), 2 for more
vertical resolution.

**Why:** it turns the fill area and buffer size problem into a small,
square-pixel canvas, which is the single biggest reason these modes are
practical for a full-screen redraw every frame.

## 3. Playfield width

`DMACTL` ($D400; shadow `SDMCTL` $022F) sets playfield width. **Narrow**
(32 bytes/line = 64 GTIA pixels) is the usual 3D choice:

- fewer bytes/line → **smaller buffers** and **less to fill**;
- ANTIC steals **less DMA**, leaving the CPU more cycles;
- the object still fills a good central area.

Normal (40 bytes = 80 pixels) is wider but costs DMA and fill. Wide is
almost never worth it for compute-heavy 3D.

## 4. Double buffering

Redrawing a whole object in view causes tearing/flicker. Keep **two screen
buffers**; draw into the hidden one, display the other, and swap on the
vertical blank. Two ways to swap:

- **Patch the LMS address** in a single display list. The display list has
  one Load-Memory-Scan operand; write its high byte to point at the other
  buffer. One store, no second display list. Best when the buffer fits
  without a 4 KB ANTIC boundary crossing.
- **Keep two display lists** (one per buffer) and point the display at the
  other one. **With the OS VBI running, write the *shadow* `SDLSTL/SDLSTH`
  ($0230/1)**, not `DLISTL/DLISTH` ($D402/3): the OS reloads the hardware
  pointer from the shadow every VBI and would overwrite a direct write.
  Costs a second display list but is trivial and handles per-line-LMS
  layouts. (Writing `$D402/3` directly is only safe with the OS VBI off.)

Synchronize the swap to the VBI so you never switch mid-frame:

```asm
        lda FRAMECT          ; a frame counter you bump in the VBI/NMI
@wait   cmp FRAMECT
        beq @wait            ; block until the next vertical blank
        ; now safe: point the display at the freshly drawn buffer,
        ; then start drawing into the other one.
```

**Why:** the viewer only ever sees complete frames; you get the whole
frame to draw the next one.

## 5. DLI colour banding

Display-list interrupts let you change colour registers partway down the
screen. In mode 9, change `COLBK` per band for different hues; in mode 10,
reload the palette per band. Combined with the shade values in the pixels,
this multiplies your apparent palette without extra per-pixel cost. Keep
DLIs short (they run on a tight cycle budget) and `sta WSYNC` before colour
writes to avoid mid-line glitches. See `graphics/display-lists.md`.

## 6. The main loop and timing

Per frame, in order:

```
1. advance angles (add per-axis deltas)
2. build rotation (matrix or per-frame LUTs)
3. rotate normals -> cull back-faces / off-screen  (culling-depth.md)
4. rotate + project surviving vertices
5. depth-sort visible faces                         (culling-depth.md)
6. clear the draw buffer's dirty box
7. walk edges -> span buffer; fill + shade spans
8. wait VBI; flip buffers
```

**Raster timing.** If you draw into the buffer that is *currently
displayed's partner*, you're safe, but if any step touches the visible
buffer, gate it on the beam position: `bit VCOUNT` / `bpl` spins until the
electron beam passes a chosen scanline, keeping writes out of the visible
area. Use a VBI/NMI-incremented frame counter to pace the loop and to time
the flip (§4).

**Measuring the budget (the raster bar).** To *see* how much of the frame
your render takes, write a bright value to `COLBK` ($D01A) at the start of a
frame's work and restore a dark one at the end. The bright band that
appears on screen is exactly the scanlines your code was busy for — if it
fills more than the frame, you're dropping frames. It costs two stores and
is the fastest way to know whether an optimization actually helped and
whether you're inside the ~30 000-cycle NTSC budget.

## 7. Bare-metal setup — reclaim cycles and RAM

For maximum performance you can switch the OS ROM off and take the machine
over. Writing `PORTB` ($D301) bit 0 = 0 unmaps the OS ROM: `$C000–$CFFF`
and `$D800–$FFFF` become RAM (only the hardware page `$D000–$D7FF` stays
I/O), and — crucially — the CPU's own vectors — NMI at `$FFFA/$FFFB`, RESET
at `$FFFC/$FFFD`, IRQ/BRK at `$FFFE/$FFFF` — are now RAM. Point NMI straight
at your handler:

```asm
        sei
        lda #0   \ sta NMIEN         ; silence NMIs while we set up
        lda #$FE \ sta PORTB         ; OS ROM + BASIC off -> RAM everywhere
        lda #<myNMI \ sta $FFFA      ; take the raw 6502 NMI vector
        lda #>myNMI \ sta $FFFB
        lda #$C0 \ sta NMIEN         ; enable DLI + VBI NMIs
        jmp mainloop
```

Your NMI handler reads `NMIST` ($D40F) to tell a DLI from a VBI, does the
per-band colour work and bumps a frame counter, and ends in `RTI`.

**Why:** you regain ~14 KB of contiguous RAM (for buffers, generated code,
tables) and every cycle the OS VBI/DLI dispatcher would have spent, and you
get interrupt latency down to the raw vector.

**The trade-offs:** you lose all OS services (I/O, keyboard, timers), you
must handle everything yourself, and you must survive **RESET** (which
re-enables the OS ROM) if you care about it — trap or re-init on reset. Do
this for a fixed-purpose effect; keep the OS for anything that needs disk,
keyboard, or coexistence. See `system/os-hardening.md`.

## 8. Data-driven scene scripts

To sequence *several* objects/effects over time without hard-coding the
schedule, drive the main loop from a **command list** (a tiny bytecode).
Each entry names what to draw and for how long:

```
entry:  tag, primitive_count, handler_addr_lo, handler_addr_hi, duration
        tag = $FF marks the end of the script
```

Byte 0 is a **tag** the interpreter tests for the `$FF` terminator; the
payload starts at offset 1. The interpreter reads the entry, **patches the
handler address into a JSR operand** and calls it, and advances to the next
entry when a frame counter passes `duration`:

```asm
        ldy #0
        lda (script),y \ cmp #$FF \ beq @end   ; tag: end of script?
        ldy #1
        lda (script),y \ sta count
        iny \ lda (script),y \ sta call+1      ; handler low
        iny \ lda (script),y \ sta call+2      ; handler high
call    jsr $0000                              ; operand self-modified above
```

**Why:** the *sequence* becomes data you can change without touching code,
and one engine renders many scenes. It's the same self-modifying dispatch
idea as the compiled fill (`rasterizer.md`, strategy (d)), applied to
control flow.

## 9. Memory budgeting (64 KB)

A typical bare-metal layout:

| Region | Contents |
|---|---|
| zero page | pointers, accumulators, the hot inner loop (self-modified) |
| low RAM | code + math tables (square, reciprocal/divide, sine) |
| mid RAM | vertex/normal/shade buffers, per-frame rotation LUTs |
| high RAM (under OS) | two screen buffers, generated fill code (double) |
| `$D000–$D7FF` | hardware (untouched) |

**Page-align** anything you index by a self-modified base byte (square
table, divide table, generated code). Put double buffers where they don't
straddle a 4 KB ANTIC boundary, or use two display lists if they do.

## See also

- `hardware/gtia.md`, `hardware/antic.md` — register-level mode/DMA detail.
- `graphics/display-lists.md` — building display lists and DLIs.
- `system/os-hardening.md` — OS-off, RESET survival, trampolines.
- `rasterizer.md` / `shading.md` — what fills these buffers.
- `culling-depth.md` — the culling and depth sort in the main loop.
