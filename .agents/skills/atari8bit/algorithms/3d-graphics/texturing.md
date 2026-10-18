# Texturing

> **Load when:** you want a bitmap texture (or fake reflections) on the
> faces instead of a flat/Gouraud shade. Builds on `rasterizer.md` (the
> zero-page self-modifying inner loop) and `shading.md` (the same
> per-pixel interpolation).

## 1. Texture mapping

Paint a stored bitmap onto each face instead of a shade.

### Affine mapping (linear)

Interpolate **texture coordinates** `(u,v)` linearly across the span, the
same way Gouraud interpolates shade — one DDA accumulator per coordinate.
Per pixel: fetch the texel `TEX[v_hi][u_hi]` and write it:

```asm
@pix    ora TEX,x            ; texel (TEX base self-modified per row)
        sta SCR,y            ; screen (SCR self-modified per column)
        ; step u (and v) by their per-pixel increments (from divide table)
        ...
        iny
        cpy width
        bcc @pix
```

Run this inner loop from **zero page with self-modified operands** (see
`rasterizer.md`, fill strategy (e)) for speed, and precompute the
per-column source offsets so the loop stays branch-free.

**Affine error:** linear `(u,v)` interpolation ignores perspective, so the
texture "swims" on faces that are large in depth. On small faces (a
rotating solid's facets) the error is invisible, so affine is the usual
choice.

### Perspective-correct mapping

For large faces, interpolate `u/z` and `v/z` linearly (they *are* linear in
screen space) and divide by `1/z` per pixel — using the reciprocal/divide
table so the divide is a lookup, not a software divide. Or **subdivide**
the span into short segments and do affine within each (perspective-correct
at the segment joints only) — cheaper and usually good enough.

**Trade:** affine is one add per coordinate per pixel; perspective-correct
adds a divide (table lookup) per pixel or the bookkeeping of subdivision.
Use affine unless faces are visibly large in depth.

### The per-pixel step comes from the divide table

For both shade and texture interpolation the per-pixel increment is
`(Δ<<8)/span_pixels` — read straight from the fixed-point divide table
(`math.md`), so setting up a span is a lookup, not a division.

## 2. Environment mapping — fake reflections for free

A cheap "chrome/shiny" look reuses the **rotated normal** you already have.
Instead of lighting it, use two components of the normal as `(u,v)` into an
**environment texture** (a small image of the surroundings), so each face
samples the environment in the direction it faces — as the object turns,
the reflection sweeps across it:

```
u = (rotated_nx >> k) + HALF        ; normal.x -> horizontal env coord
v = (rotated_ny >> k) + HALF        ; normal.y -> vertical   env coord
pixel = ENVMAP[v][u]
```

It's just texture mapping with the texture coordinates driven by the normal
instead of by fixed per-vertex UVs — same fill machinery. Interpolate the
normal across the face (like Gouraud) for a smooth sweep, or use one normal
per face for a faceted look. **Why it's cheap:** no lighting math and no
stored UVs — the normal is already rotated for culling/shading, so the
reflection is nearly free. **Limitation:** it's a *view-independent*
approximation (the "reflection" doesn't account for camera position), but it
reads convincingly on a spinning solid.

## See also

- `rasterizer.md` — the zero-page self-modifying inner loop the texel
  fetch runs in.
- `shading.md` — the same per-pixel interpolation, applied to shade.
- `rotation.md` — the rotated normal that drives environment mapping.
