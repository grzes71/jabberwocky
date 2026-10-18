# Culling and depth sort

> **Load when:** you need to drop hidden faces and order the visible ones
> for correct overlap. Sits between `projection.md` and `rasterizer.md` in
> the main loop (`display.md` §6).

## 1. Back-face culling

Don't rasterize faces pointing away from the camera.

- **Screen-space cross-product sign.** After projection, for a face's
  first three screen vertices, `cross = dx0·dy1 − dx1·dy0`. Its sign tells
  you the winding; one sign is front-facing, the other is back. Reject the
  back set. Works after projection, needs one multiply pair.
- **Object-space pre-transform reject (cheapest).** Rotate only the *view
  direction* into object space once per frame. Build three small 256-entry
  tables from its components, `VX[n]=viewX·n`, `VY[n]=viewY·n`,
  `VZ[n]=viewZ·n` — using the **signed** two-ramp build from `rotation.md`
  §3, because normal components are signed (indices 128..255 are the
  negative values). Then the dot of the view with each face's stored normal
  `(nx,ny,nz)` is **three lookups and two adds — no multiply** — and faces
  failing it are dropped **before** you rotate and project their vertices:

```asm
@face   ldy nx,x \ lda VX,y \ sta d      ; viewX * nx
        ldy ny,x \ lda VY,y \ clc \ adc d \ sta d
        ldy nz,x \ lda VZ,y \ clc \ adc d
        bmi @hide            ; dot < 0 -> facing away, skip entirely
        ; (optional) also reject if too deep for a distance cull
        ...record as visible...
@hide   inx
        cpx face_count
        bne @face
```

**Why object-space:** culling before transform can remove ~40% of the work
up front — the largest single saving in a solid renderer.

## 2. Depth sorting — bucket sort

For correct occlusion without a z-buffer (there's no RAM/time for one),
draw back-to-front (painter's algorithm), which needs the visible faces
**sorted by depth**. Depth keys are bytes, so a **bucket sort** is O(N)
with zero comparisons:

```asm
        ; scatter: bucket = depth >> k. Here >>3 of a 0..255 depth gives
        ; 32 buckets; shift more for fewer, coarser buckets.
@fill   lda depth,x
        lsr \ lsr \ lsr
        tay
        lda bkt_head,y       ; push onto a linked list per bucket
        sta link,x
        txa
        sta bkt_head,y
        inx
        cpx vis_count
        bne @fill
        ; gather: walk buckets far->near, follow links -> sorted order
```

**Why buckets:** depth keys are small integers, so shifting gives the
bucket directly; no compares, linear time, trivial. Compare-based sorts
(insertion, comb, quick) are only worth it for very small N or non-uniform
keys — see `algorithms/sorting.md`.

**Note:** the painter's algorithm handles convex, non-interpenetrating
solids. Faces that mutually overlap in depth need splitting (a BSP-style
approach), which is rarely worth it on this hardware — design meshes to
avoid it.

## See also

- `rotation.md` — the rotated normal and the signed table build this reuses.
- `algorithms/sorting.md` — depth-sort alternatives (comb, insertion, quick).
- `display.md` — where culling and sorting sit in the frame loop.
