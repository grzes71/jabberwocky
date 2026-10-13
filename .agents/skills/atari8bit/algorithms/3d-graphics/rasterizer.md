# Rasterization: edges, spans, and fast fill

> **Load when:** you have projected 2-D vertices and must fill the polygon.
> This is where most of a frame's cycles go, so it is where the exotic
> speed tricks live.

## 1. Span buffer — decouple edge walking from filling

Rather than fill each polygon directly, most fast renderers build a
**span buffer**: two arrays indexed by scanline,

```
SPAN_XL[y] = leftmost x on scanline y     (init to $FF = "none")
SPAN_XR[y] = rightmost x on scanline y    (init to 0)
```

Walk every edge, updating `min` into `SPAN_XL[y]` and `max` into
`SPAN_XR[y]` for each scanline the edge crosses. Then a single pass fills
`SPAN_XL[y]..SPAN_XR[y]` on each row, skipping rows where `XL > XR` — the
untouched `$FF`/`0` sentinel pair marks a scanline the polygon misses.

**Why a span buffer:** it cleanly handles convex polygons (quads,
triangles) regardless of vertex order, separates the (branchy) edge logic
from the (tight) fill loop so each can be optimized independently, and lets
you attach *per-scanline* attributes (like interpolated shade — see
`shading.md`/`texturing.md`). Keep `SPAN_XL`/`SPAN_XR` inside a single 256-byte
page so the `y`-indexed accesses never cross a page and cost extra cycles.

**Convex only.** One left/right pair per scanline assumes the polygon is
**convex** — each scanline enters and leaves it exactly once. Triangles and
convex quads are always fine, which is why solid meshes are built from
them. A *concave* face has scanlines that cross it more than twice; those
need a full active-edge table (a list of crossings per scanline), which is
much slower — so tessellate concave faces into convex pieces instead.

**Clamp to the screen.** Before storing a crossing, clip `x` to
`0..width-1` and skip scanlines outside `0..height-1`. Projected vertices
can land off-screen (a partially-visible object), and an unclamped `x` or
`y` will index outside the span/screen buffers and corrupt memory. The edge
walk below elides the clamp for brevity, but a real one tests it every row.

## 2. Edge walking — Bresenham vs DDA

Both compute, for each scanline `y`, the `x` where an edge crosses it.

### Bresenham (integer error accumulator, no division)

```asm
; walk from (x0,y0) to (x1,y1), storing x into the span buffer per row
WalkEdge
        ; dy = y1-y0 ; adx = |x1-x0| ; xstep = ±1
        lda #0
        sta err
        ldy y0
        lda x0
        sta cx
@row    ; store cx into SPAN_XL[y] if smaller, SPAN_XR[y] if larger
        ...
        lda err
        clc
        adc adx
        sta err
@carry  cmp dy
        bcc @next
        sbc dy
        sta err
        lda cx
        clc
        adc xstep
        sta cx
        lda err
        jmp @carry           ; x may step >1 per scanline (steep-in-x edges)
@next   iny
        cpy y1
        bcc @row
        rts
```

**Why Bresenham:** needs no division and no tables — just adds and
compares — and is exact, as long as the accumulator fits in a byte: `err`
stays below `dy` and grows by `adx` per row, so the walk is only safe while
`adx + dy ≤ 255`. A shallow edge (roughly `adx > 255 − dy`) overflows and
the x values drift — e.g. `(30,5)-(220,120)` (`adx`=190, `dy`=115) ends at
x=104 instead of 218. Use a 16-bit error for those, or clip such edges out.
It is the default when you don't already have a reciprocal handy.

### DDA (fixed-point slope from a reciprocal table)

If you already carry a divide/reciprocal table (`math.md`), precompute the
slope `dx/dy` once and add it to an 8.8 accumulator each scanline:

```asm
        ; slope = (dx<<8)/dy  from the divide table (one lookup).
        ; Stored two's-complement so a signed (leftward) slope also works.
@row    clc                  ; start the 16-bit add fresh each row
        lda frac
step    adc #slope_lo        ; slope_lo self-modified per edge
        sta frac
        lda cx_hi
        adc #slope_hi        ; carry from frac propagates the integer step
        sta cx_hi            ; integer x = cx_hi
        ...store span...
        iny
        cpy y1
        bcc @row
```

**Why DDA:** the inner loop is one add per scanline (no compare/branch for
the step), which is slightly tighter than Bresenham *if* the slope lookup
is free because you have the table anyway. **Trade:** it needs the table
and a per-edge divide to get the slope; Bresenham needs neither. Pick DDA
when a reciprocal table is already resident for shading/texture; pick
Bresenham for a lean, table-free renderer.

## 3. The five fill strategies

Filling `SPAN_XL[y]..SPAN_XR[y]` is the hottest loop in the program.
Ordered from simplest to fastest-and-most-specialized:

### (a) Indexed byte fill — the baseline

```asm
        ldy byte_l           ; fill [byte_l, byte_r] inclusive
        lda colour
@f      sta (scr),y
        cpy byte_r
        beq @+               ; stop after writing byte_r (handles l == r)
        iny
        bne @f
@
```

Simple, general, ~16 cycles/byte (measured: `sta (scr),y` is 6 cycles
before any loop overhead). Fine for small spans or a first cut.

### (b) Nibble-aware fill — for 4-bit (GTIA) modes

GTIA luminance modes pack **two pixels per byte** (a high and a low
nibble; see `display.md`). A span may start or end on an odd pixel,
so the partial end bytes need read-modify-write to preserve the
neighbouring pixel, while the middle is whole bytes:

```asm
        ; byte_l = xl>>1, byte_r = xr>>1 computed first.
        ; left partial: if xl is odd, its pixel is the low nibble of byte_l
        lda xl
        and #1
        beq @mid             ; even xl -> byte_l is a whole byte, no partial
        ldy byte_l
        lda (scr),y
        and #$F0             ; keep left neighbour's high nibble
        ora shade            ; our pixel in low nibble
        sta (scr),y
        inc byte_l           ; whole-byte fill starts at the next byte
@mid    ; right partial: if xr is even, patch high nibble only (symmetric)
        ...
        ; middle whole bytes: write shade_pair (shade in both nibbles)
        ldy byte_l
        lda shade_pair
@f      sta (scr),y
        cpy byte_r
        beq @+
        iny
        bne @f
@       rts
```

Precompute `shade_pair = (shade<<4) | shade` once so whole bytes are a
single store. **Why:** correct 4-bit fill without clobbering adjacent
pixels; the middle stays as fast as (a).

### (c) Unrolled fill — remove the loop

For spans of bounded length, or for writing one value down *many rows at
once* (a vertical run), emit a straight line of stores with no counter:

```asm
; X = the byte offset within the line; STRIDE = bytes per scanline.
        lda shade_pair
        sta SCR+0*STRIDE,x   ; scanline 0
        sta SCR+1*STRIDE,x   ; scanline 1
        sta SCR+2*STRIDE,x   ; scanline 2
        ...                  ; N unrolled stores, one per scanline
```

(Use absolute-indexed stores with a constant per-line stride — you can't
offset a zero-page indirect pointer inline.)

**Why:** deletes the `cpy/bne` (~3 cyc) *and* the index arithmetic per
iteration. **Trade:** only works when the count is known/bounded at
assembly time; costs code space proportional to the run.

### (d) Runtime-generated ("compiled") fill — the fastest

Generate the fill routine *as machine code* during setup, tailored to the
current object, then `JSR` it. The generator writes opcode + operand bytes
into a RAM buffer:

```asm
; Emit: one "lda #shade" ($A9 val), then a run of "sta addr" ($8D lo hi),
; then "rts" ($60). The fill value is loaded once; every pixel is a bare
; store to a hard-coded address.
        ldy #0
        lda #$A9 \ sta (code),y \ iny      ; LDA #imm
        lda shade \ sta (code),y \ iny
@emit   lda #$8D             ; opcode for STA abs
        sta (code),y
        iny
        lda addr_lo,x        ; target byte address, low
        sta (code),y
        iny
        lda addr_hi,x
        sta (code),y
        iny
        ...                  ; repeat STA per byte; finish with $60 (RTS)
        ; later, each frame:
        jsr code_buffer
```

**Why:** the executed fill has *zero* loop overhead and *zero* address
arithmetic — every pixel is one hard-coded store, the theoretical floor.
This is the single most effective fill technique on the platform.
**Trade:** you spend cycles *generating* the code (amortized if the shape
is stable across frames), it consumes RAM for the code buffer, and it is
intricate to get right. **Double-buffer the generated code** (two buffers)
so one is executing while the next is being built, mirroring the screen
double buffer.

### (e) Zero-page self-modifying inner loop — for per-pixel work

When the inner loop must do work per pixel (texture fetch, shade
interpolation) you can't fully unroll it, but you can make each iteration
minimal by running the loop **from zero page** and **self-modifying its
source/destination operands**:

```asm
; this loop is copied into zero page at $0090 first; operands patched per column
ZPLOOP  ora TEX,x            ; TEX low/high self-modified per span
        sta SCR,y            ; SCR low/high self-modified per span
        ; ...advance texture coordinate (DDA)...
        iny
        cpy #width
        bcc ZPLOOP
```

**Why zero page:** *not* faster instruction fetch — the 6502 fetches
opcodes at one cycle per byte wherever the code lives. The wins are two:
the loop's own data accesses can use **zero-page addressing** (a 1-byte
operand, a cycle cheaper than absolute), and putting the body in RAM makes
it convenient to **self-modify**. **Why self-modify:** patching the source
and destination operand *addresses* once per column removes per-pixel
address computation entirely — the real speed-up. **Trade:** brittle,
consumes zero-page space, and must be re-patched whenever the addresses
change. This is the texture-mapper's equivalent of (d).

### Choosing a fill

| Situation | Strategy |
|---|---|
| First implementation / small spans | (a) indexed byte |
| Any 4-bit GTIA shaded mode | (b) nibble-aware (as the base of the others) |
| Bounded/known span or vertical runs | (c) unrolled |
| Fixed object, want maximum flat-fill fps | (d) runtime-generated code |
| Per-pixel inner loop (texture, gouraud) | (e) zero-page self-modifying |

## 3a. Points and wireframe (the cheaper render modes)

Before (or instead of) filling, you can draw a model as **points** (one
pixel per vertex) or **wireframe** (a line per visible edge). They're far
cheaper than filling and invaluable while bringing a renderer up — if the
points/edges track correctly, your transform and projection are right and
only the fill is left to debug.

- **Points:** plot each projected vertex with the nibble read-modify-write
  from fill (b) — set one pixel, keep its neighbour.
- **Wireframe:** draw each front-facing edge with a **Bresenham line**. The
  general (any-slope) line steps along the major axis and accumulates error
  to step the minor axis:

```asm
; Bresenham line, y-major case (|dy| >= |dx|).  dx=|x1-x0|, dy=|y1-y0|,
; sx/sy = the ±1 direction steps.  err and the ±2*dx / ±2*dy terms are
; 16-bit signed — on a full-length line 2*max(dx,dy) exceeds a signed byte,
; so test err's HIGH byte.  The x-major case is symmetric (swap x<->y).
DrawLine
        ; err = 2*dx - dy   (16-bit, in err_lo/err_hi)
@yl     jsr PlotPixel            ; plot (x,y): nibble RMW from fill (b)
        lda y \ cmp y1 \ beq @done
        lda err_hi
        bpl @stepx               ; err >= 0 -> also step the minor axis (x)
        ...err += 2*dx (16-bit)...
        jmp @stepy
@stepx  ...err += 2*dx - 2*dy (16-bit)...
        lda x \ clc \ adc sx \ sta x
@stepy  lda y \ clc \ adc sy \ sta y   ; major axis steps every iteration
        jmp @yl
@done   rts
```

**Why keep them:** points/wireframe are a diagnostic *and* a valid low-cost
render mode (a spinning wire object costs a fraction of a filled one). Pick
the major axis (the one with the larger delta) so the inner loop steps one
pixel along it per iteration — that keeps the line gap-free.

## 4. Clearing the buffer — only what you drew

Clearing the screen each frame can cost as much as filling it. Two levels:

- **Full clear:** zero the whole buffer with an 8×-unrolled `sta`. Simple.
- **Dirty bounding box:** track the min/max scanline actually drawn this
  frame; next time you draw into that buffer (two frames later, with
  double buffering), clear only that page range:

```asm
        ; start_page = ymin>>3 ; end_page = (ymax>>3)+1   (32 bytes/line)
@page   .rept 8
        sta (ptr),y
        iny
        .endr
        bne @page
        inc ptr+1
        dex
        bne @page
```

**Why:** a rotating object usually covers a fraction of the screen; a
dirty-box clear of ~half the buffer saves thousands of cycles a frame.
Keep a *separate* saved bbox per buffer (double buffering means each buffer
was last drawn two frames ago). Reset the live bbox to an empty sentinel at
the start of each frame's drawing.

## See also

- `math.md` — the divide table behind DDA slopes.
- `shading.md`/`texturing.md` — Gouraud/texture fills built on (b)/(e).
- `display.md` — GTIA nibble pixel format, double buffering, timing.
- `graphics/software-sprites.md` — related span/fill and dirty-buffer ideas.
