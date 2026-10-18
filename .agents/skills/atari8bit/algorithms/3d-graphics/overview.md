# Overview

Everything needed to build a filled, shaded, or textured rotating-solid
renderer that runs at a usable frame rate on a stock 1.79 MHz 6502 with
ANTIC + GTIA. Read this, then open the smallest matching topic file.

## The problem, in one paragraph

A filled 3D object needs, every frame: a few dozen vertices rotated
(multiplies), projected (divides), edges walked, spans filled, and pixels
shaded — thousands of multiplies and divides. The 6502 has **neither a
multiply nor a divide instruction**, ~30 000 CPU cycles per NTSC frame
(~35 500 on PAL's slower 50 Hz refresh; fewer once ANTIC steals DMA), and
64 KB of address space shared with screen memory. Every technique here
exists to beat that budget.

## The central idea: trade memory and generality for cycles

Fast 3D on this machine is won by **precomputing** and **specializing**:

1. **Turn arithmetic into table lookups.** Multiply, divide/reciprocal,
   sine/cosine, square root — all become `lda table,x`. → `math.md`
2. **Remove loop overhead from the hot path.** Unroll fills, *generate*
   the inner loop as machine code at run time, or run it from **zero page
   with self-modified operands.** → `rasterizer.md`
3. **Draw into a hidden buffer and flip on the vertical blank.** No
   tearing, and you can spend the whole frame drawing. → `display.md`
4. **Only touch what changed.** Clear the drawn bounding box, not the
   whole screen; cull and depth-sort so you rasterize fewer, correctly
   ordered polygons. → `rasterizer.md`, `culling-depth.md`
5. **Pick a display mode that gives you shade *for free*.** GTIA
   luminance modes hand you 16 grey/one-hue levels or 9 colours as a
   4-bit value per pixel — no dithering needed. → `display.md`

The price is memory (tables, generated code, double buffers) and rigidity
(a specialized renderer is fast but hard to change). A general engine
makes the opposite trade. Neither is "correct"; choose per goal.

## The pipeline (per frame)

```
 angles += Δ ─► build rotation (matrix or LUT)
                        │
                        ▼
                rotate vertices ─► cull back-faces / off-screen
                        │
                        ▼
                project to 2-D (perspective or 2.5D) ─► depth-sort
                        │
                        ▼
   flip buffer ◄─ fill spans + shade ◄─ walk polygon edges
   (on VBI)        (byte / nibble / unrolled / compiled / ZP)
```

## Topic files

| Open | For |
|---|---|
| **`math.md`** | Fixed-point formats; quarter-square multiply; divide/reciprocal tables; sine (quarter-wave + folding); sqrt. |
| **`rotation.md`** | Rotation matrices vs rotation LUTs vs incremental rotation; angle animation; mesh & normal data. |
| **`projection.md`** | Perspective and 2.5D projection; near-plane / clipping; transforming normals. |
| **`rasterizer.md`** | Edge walking (Bresenham vs DDA); span buffer; five fill strategies; wireframe; fast clearing. |
| **`shading.md`** | Flat and Gouraud shading; N·L lighting with fast paths; direct-shade vs dither. |
| **`texturing.md`** | Affine and perspective-correct texture mapping; environment mapping. |
| **`display.md`** | GTIA 9/10/11 modes; VSCROL square-pixel trick; playfield width; double buffering; DLI banding; the main loop; bare-metal setup; scene scripts; memory budgeting. |
| **`culling-depth.md`** | Back-face culling; depth bucket sort. |

## Decision guide — which approach?

| If your goal is… | Lean toward |
|---|---|
| Maximum frame rate for **one fixed object/effect** | LUT or compiled inner loops, precomputed rotation, bare-metal, narrow playfield |
| A **reusable engine** (swap meshes, lighting, modes) | Matrix rotation computed live, table-driven but general fill, keep it modular |
| **Smooth shading** with real luminance | GTIA 9 (16 grey/one-hue) + Gouraud, no dither |
| **Colour** shading | GTIA 10 (9 colours) + Gouraud over a colour ramp |
| **Few** vertices per frame | Compute the rotation matrix live (cheap to build) |
| **Many** vertices per frame | Build per-frame rotation LUTs (amortize the build) |
| **Textured** faces | ZP self-modifying texel loop; affine unless faces are large |
| **Lowest memory** | Live matrix multiply + Bresenham (no big tables); accept lower fps |

---
