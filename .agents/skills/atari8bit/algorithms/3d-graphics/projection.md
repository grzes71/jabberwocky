# Projection

> **Load when:** you have rotated camera-space vertices and must place them
> on the screen. Follows `rotation.md`.

After rotation you have camera-space `x,y,z`. Convert to screen pixels.

## 1. Full perspective

```
zi   = z + CAM_DIST            ; shift so the nearest depth ≥ ZMIN
scrX = CX + (x · RECIP[zi]) >> 8
scrY = CY − (y · RECIP[zi]) >> 8
```

`RECIP[zi] = FOCAL·256/zi` (see `math.md`). One multiply + one lookup per
axis. Clamp `zi` to at least `ZMIN = ceil(FOCAL·256/255)` — a byte table
only holds `RECIP ≤ 255`, so `zi = 0` is undefined and `zi < ZMIN` wraps
the byte; use 16-bit entries if you must divide by small depths.

## 2. The near plane — why `zi` must be clamped

Perspective divides by depth, so a vertex *at* the camera (`zi = 0`) or
*behind* it (`zi ≤ 0` before the `+CAM_DIST` shift) produces an infinite or
wrapped screen coordinate — garbage that can scribble across the whole
buffer. Guard it:

- **Keep the object in front.** Choose `CAM_DIST` so the *nearest possible*
  rotated `z` still gives `zi ≥ 1`. For a small solid that never
  approaches the camera, this alone is enough and needs no per-frame test.
- **Clamp `zi`** to a minimum (e.g. `1`) before the `RECIP` lookup as a
  cheap safety net.
- **Full near-plane clipping** — splitting a face that straddles the camera
  plane and interpolating a new edge vertex at `z = near` — is correct but
  expensive; most fixed-object renderers avoid it by construction (keep the
  whole object in front) rather than implementing it.

Also **clamp the projected `scrX`/`scrY` to the screen** (or reject
off-screen vertices) before rasterizing, so the edge walk never indexes
outside the span/screen buffers — see `rasterizer.md`.

## 3. 2.5D shortcut — perspective in Y only

A widely used cheat: project **Y with perspective but X orthographically**:

```
scrX = CX + x                       ; signed byte add, no divide, no multiply
scrY = CY − (y · RECIP[zi]) >> 8    ; perspective only in Y
```

**Why it works and when:** for objects that are wider than deep and viewed
head-on, the horizontal perspective error is small, and you save a
multiply *and* a reciprocal lookup per vertex — a big inner-loop win.
**When not:** objects with strong depth along X, or a rotating camera, will
show the shear. Use full perspective for a general engine, the 2.5D
shortcut for a fixed-viewpoint effect.

`RECIP[zi]` is unsigned (it can exceed 127), so multiply by `|y|` with
`UMult8` and then **restore the sign** by adding or subtracting the offset
from the screen centre — subtracting always would put negative-`y` points
on the wrong side:

```asm
projY   lda vz
        clc
        adc #CAM_DIST        ; zi = depth + camera distance
        tax                  ; (clamp zi to ZMIN..255 before use)
        lda RECIP,x
        sta mb               ; scale = RECIP[zi]  (unsigned)
        lda vy
        bpl @pos
        eor #$FF \ clc \ adc #1     ; |y|
        sta ma
        jsr UMult8           ; |y|*scale ; integer part in prod_hi
        lda CY
        clc
        adc prod_hi          ; y < 0  -> below the centre line
        sta scrY
        rts
@pos    sta ma
        jsr UMult8
        lda CY
        sec
        sbc prod_hi          ; y > 0  -> above the centre line
        sta scrY
        rts
```

## 4. Transforming normals (for lighting and culling)

Lighting and back-face tests need the face/vertex **normal in the rotated
frame**. Two options:

- **Rotate the normal like a vertex** (same matrix or LUTs). Correct for
  any rotation.
- **Object-space test:** rotate only the *view direction* into object
  space once per frame and dot it against each stored (un-rotated) normal.
  This lets you reject back-faces *before* transforming their vertices —
  the cheapest culling (see `culling-depth.md`).

Store normals in the same fixed-point format as coordinates so they reuse
the same multiply/LUT machinery.

## 5. Choosing

Full perspective for a real engine or a rotating camera; the 2.5D X-ortho
shortcut when the viewpoint is fixed and you want the cycles back.

## See also

- `rotation.md` — producing the camera-space vertices this projects.
- `math.md` — the reciprocal/divide table behind perspective.
- `rasterizer.md` — filling the projected polygons.
