# Shading

> **Load when:** your polygons fill but you want them lit or smoothly
> shaded. Builds on `rasterizer.md` (spans, nibble fill) and `math.md`
> (multiply, reciprocal, divide table).

The key enabler is the display: a GTIA luminance mode gives you a **4-bit
value per pixel** — 16 grey/one-hue levels (mode 9) or 9 colours (mode
10). So "shade" is just a number 0..15 you write into a nibble, and smooth
shading needs no dithering. See `display.md` for the mode setup; the rest
of this file assumes 4-bit pixels.

## 1. Flat shading

One shade for the whole polygon. Compute a lighting value once per face
(see §2), pack it into both nibbles (`shade_pair = shade<<4 | shade`), and
use the fast nibble-aware fill. Cheapest correct shading; good default.

## 2. Lighting — per-vertex N·L

Diffuse lighting is the dot product of the surface normal `N` and the
light direction `L`, both unit vectors: `intensity = N·L`, mapped to a
shade. Compute per face (flat) or per vertex (Gouraud).

### Full dot product (~350 cycles)

```asm
        lda nx \ ldx lx \ jsr SMult8 \ sta dot         ; nx*lx
        lda ny \ ldx ly \ jsr SMult8 \ clc \ adc dot \ sta dot
        lda nz \ ldx lz \ jsr SMult8 \ clc \ adc dot   ; + nz*lz
        asl                      ; SMult8 returns each product's high byte,
        ;  which is Q1.7/2 -> one ASL restores Q1.7
        clc \ adc #$80           ; bias signed -> 0..255
        tax
        lda SHADE_TAB,x          ; 256-entry LUT -> pixel value 0..15
```

`SHADE_TAB` is a full 256-entry table indexed by the *whole* biased
intensity byte — **not** `intensity AND $0F`, which would alias distant
intensities to the same nibble. The table does the shaping: clamp negative
intensities to the darkest level, spread the positive range across the
0..15 (mode 9) or 0..8 (mode 10) shade values, apply a ramp/gamma — all
without extra math.

### Equal-light fast path (~25 cycles)

If the light's components are equal (`lx == ly == lz`), the dot product
collapses to a scaled sum of the normal's components — **no multiply**:

```
N·L ∝ nx + ny + nz
```

```asm
        lda nx \ clc \ adc ny \ clc \ adc nz
        tax
        lda SHADE_SUM_TAB,x      ; sum -> shade, direct LUT
```

Scale the stored normals so `nx+ny+nz` stays within the table's index
range (a signed byte, biased), then `SHADE_SUM_TAB` maps the sum straight
to a shade — the same shaping table idea as above.

**Why keep both:** a fixed diagonal light is common and this path is an
order of magnitude faster (measured ~25 vs ~370 cycles); fall back to the
full product only when the light isn't diagonal. Detect the case at build
time and assemble only the path you need.

## 3. Gouraud shading — smooth across the face

Compute a shade at each **vertex**, then interpolate it across the
polygon. Two interpolations: along each edge (to get left/right shade per
scanline) and across each span (left→right).

### Edge: shade interpolation parallel to the X walk

Run a **second accumulator** alongside the edge's X walk (Bresenham or DDA
from `rasterizer.md`), stepping the shade from the top vertex's value to
the bottom vertex's value. Store the shade at the scanline where you set
`SPAN_XL`/`SPAN_XR` into parallel arrays `SPAN_SL[y]`/`SPAN_SR[y]`:

```asm
@row    ...update SPAN_XL/XR and, when you do, store gs_cur into SPAN_SL/SR...
        ; shade Bresenham (parallel to the X error accumulator)
        lda gs_err
        clc
        adc gs_adelta        ; |shade1-shade0|
        sta gs_err           ; persist the error EVERY row (even non-stepping)
@s      cmp dy
        bcc @xstep
        sbc dy
        sta gs_err
        lda gs_cur
        clc
        adc gs_step          ; ±1
        sta gs_cur
        lda gs_err
        jmp @s
```

The `sta gs_err` right after the add is essential: on a scanline that
accumulates error but doesn't yet cross `dy`, `bcc @xstep` leaves with the
new value only in `A`; without the store the next row reloads the *old*
`gs_err` and the shade interpolation stalls. (Same shape as the edge X
walk in `rasterizer.md`, which stores its error every row too.)

### Span: dual-path fill

For each scanline you now have left shade `SL` and right shade `SR`.
**If they are equal**, do a plain flat nibble fill (fast). **If they
differ**, interpolate per pixel with a shade Bresenham/DDA across the span,
writing each pixel's shade into its nibble:

```asm
        lda SPAN_SL,y
        cmp SPAN_SR,y
        beq @flat_fill       ; common case — cheap
@grad   ; per-pixel: even pixel -> high nibble, odd -> low nibble
        lda cx \ lsr \ tay \ bcs @odd
        ldx gs_cur
        lda (scr),y \ and #$0F \ ora SHADE_HI,x \ sta (scr),y   ; SHADE_HI[x]=x<<4
        jmp @adv
@odd    lda (scr),y \ and #$F0 \ ora gs_cur \ sta (scr),y
@adv    ; step shade Bresenham; inc cx; loop to right edge
```

**Why dual-path:** on a smoothly shaded solid a large fraction of spans
have equal or nearly-equal end shades (flat tops/bottoms of the object),
so the cheap path handles most rows and the expensive per-pixel path only
runs where the gradient is steep. A `SHADE_HI[x] = x<<4` table avoids four
`ASL`s per even pixel.

**Why this beats dithering:** with 16 real luminance levels you write the
interpolated value directly; the gradient is genuinely smooth. Dithering
is only for modes that *don't* have enough levels (next section).

## 4. Direct shade vs ordered dithering

- **Direct shade (preferred):** in a GTIA luminance mode you have 9–16
  levels; write the shade value into the pixel. Simplest and cleanest.
- **Ordered dithering (only if forced):** in a mode with few colours
  (e.g. a 4-colour multicolour bitmap), you fake extra levels by choosing a
  **pixel pattern** per intensity from an `intensity → pattern` table, so
  neighbouring pixels alternate between the available colours and the eye
  blends them. It doubles as your fill value.

**Rule:** if the display gives you enough levels, do *not* dither — it
only adds noise and code. Reach for dithering exclusively when the chosen
mode can't represent the shades you need. For shaded 3D, prefer a GTIA
luminance mode and skip dithering entirely.

## See also

- `rasterizer.md` — spans and the fills this builds on.
- `texturing.md` — texture and environment mapping (same interpolation).
- `display.md` — GTIA luminance modes that make direct shade possible.
- `math.md` — the dot-product multiply and the interpolation divide table.
