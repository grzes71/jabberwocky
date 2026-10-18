# Rotation

> **Load when:** you have vertices and need them rotated each frame.
> Assumes the primitives in `math.md` (quarter-square multiply, sine
> tables, reciprocal).

## 1. Model and coordinate conventions

- Store vertices as signed bytes (or Q-scaled bytes) `x,y,z`. Keep the
  object centred on the origin so rotation is about its middle.
- Use a **binary angle** per axis (`0..255` = full turn) so rotation is
  angle-addition with free wraparound.
- Camera looks down `−Z` (object in front has larger/positive `z` after a
  camera offset). Screen `x` grows right, `y` grows down, so projected `y`
  is usually *subtracted* from the screen centre.

**Mesh storage.** A model is two arrays: a **vertex list** (`x,y,z` per
vertex, signed bytes) and a **face list** (each face = a few *indices* into
the vertex list, e.g. 3 for triangles or 4 for quads). Storing faces as
indices means each shared vertex is rotated **once**, not once per face —
the biggest saving for a closed solid. Keep a consistent winding order (all
faces clockwise, or all counter-clockwise) so the back-face test has a
consistent sign.

**Normals.** A face normal is `edge1 × edge2` (the cross product of two of
its edges). Because the mesh is **rigid**, compute all normals *once at
build time* (offline, in the table generator) and store one signed-byte
`nx,ny,nz` per face. At run time you only *rotate* the stored normal with
the same matrix/LUTs as a vertex — never recompute it. This feeds lighting
(`shading.md`) and culling (`culling-depth.md`).

There are three ways to rotate, in increasing setup cost and decreasing
per-vertex cost. Choose by vertex count.

## 2. Method A — a matrix built each frame

Compose axis rotations into one 3×3 matrix, then apply it to every vertex.
Two axes (pitch `x`, yaw `y`) are usually enough for a tumbling solid:

```
Ry = [ cy  0  -sy ]      Rx = [ 1   0    0 ]
     [ 0   1   0  ]           [ 0   cx   sx ]
     [ sy  0   cy ]           [ 0  -sx   cx ]

M = Ry·Rx = [ cy      sy·sx     -sy·cx ... ]   (9 signed coefficients)
```

Build `M` once per frame from the two angles using sine lookups and a few
signed multiplies (`SMult8` + renormalize) — four products (`sy·sx`,
`sy·cx`, `cy·sx`, `cy·cx`), so ~400 cycles of setup at `math.md`'s ~98
cycles per signed multiply.
Then per vertex:

```asm
; x' = m00*x + m01*y + m02*z   (and similarly y', z')  — 9 SMult8 total
```

**Cost:** cheap to *build* (constant, ~400 cyc), but ~9 multiplies per
vertex. **Use when** you have few vertices, or want a general engine where
the mesh can change — nothing about `M` depends on the model.

## 3. Method B — per-frame rotation lookup tables

When you rotate *many* vertices through the *same* matrix, replace the
per-vertex multiply with a lookup. For each matrix element `m` build a
256-entry signed table `ROT_m[v] = (m · v) >> s` covering all possible
coordinate values `v`. Then the transform is pure lookups:

```asm
; x' = ROT_m00[x] + ROT_m01[y] + ROT_m02[z]   — 3 lookups + 2 adds, no mul
        ldx vx
        lda ROT_M00,x
        ldy vy
        clc
        adc ROT_M01,y
        ldy vz
        clc
        adc ROT_M02,y
        sta out_x
```

Nine such tables cover a full 3×3 transform. **Build them without
multiplying:** `ROT_m[v] = m·v` is an arithmetic progression, so each entry
is the previous **plus `m`** — one add per entry, not a multiply.

**Watch the sign.** Coordinates are *signed* bytes, but a byte index is
*unsigned* 0..255 — indices 128..255 are the negative coordinates
−128..−1. So `ROT_M[i]` must hold `m·signed(i)`, not `m·i`. Build the two
halves as separate ramps from zero (each seeds cleanly at `m·0`):

```asm
; ROT_M[i] = m * signed_coord(i), high byte (truncated; add #$80 to the
; low byte before storing the high byte if you want rounding).
; m = signed 8.8 in melem_lo/hi.
; Positive coords 0..127 land at indices 0..127; negatives -1..-128 at 255..128.
buildRotTab
        lda #0 \ sta lo \ sta hi          ; acc = m*0
        ldy #0                            ; --- positive half: 0..127 ---
@pos    lda hi \ sta ROT_M,y              ; integer part of m*v
        clc
        lda lo \ adc melem_lo \ sta lo    ; acc += m
        lda hi \ adc melem_hi \ sta hi
        iny
        cpy #128
        bne @pos
        lda #0 \ sta lo \ sta hi          ; acc = m*0 again
        ldy #255                          ; --- negative half: -1..-128 ---
@neg    sec
        lda lo \ sbc melem_lo \ sta lo    ; acc -= m  (so index 255 = m*-1)
        lda hi \ sbc melem_hi \ sta hi
        lda hi \ sta ROT_M,y
        dey
        cpy #127
        bne @neg
        rts
```

A single ramp from index 0 (`acc += m` for all 256 entries) is the easy
mistake — it gives `m·v` for unsigned `v`, so every negative coordinate
comes out wrong by `256·m`.

**Double-fill micro-optimization.** If the coordinate is effectively 7-bit
signed (−64..63) then index `i` and index `i+128` must hold the same value,
so each computed value can be written twice — to `y` and to `y+128` — and
128 additions fill the 256-byte table, halving the build loop (the lookup
still indexes with the coordinate's plain 8-bit value: −1..−64 land at
255..192). It's a minor refinement of the loop above, not a different
algorithm.

**Cost:** higher setup (build 9 tables), zero multiplies per vertex.
**Use when** vertex count is high enough that the build pays for itself
(rule of thumb: more than ~1 table-build's worth of vertices per element).
**Downside:** several KB of table RAM, and the mesh's coordinate range is
baked into the tables.

## 4. Method C — incremental (matrix-free)

To spin by a *fixed small angle each frame*, you can skip trig entirely
with a recurrence:

```
x' = x − y·k
y' = y + x'·k          (note: uses the updated x')
```

`k ≈ Δθ` (in radians, as a small fixed-point constant); one
multiply-by-constant per axis. The object's own coordinates carry the
rotation state frame to frame.

**Why this specific form is stable.** Because the second line uses the
*updated* `x'`, the transform matrix is `[[1, −k],[k, 1−k²]]`, whose
determinant is exactly 1 — so in exact arithmetic it is **area-preserving
and does not blow up**, unlike the naïve `y' = y + x·k` (determinant
`1+k²`), which spirals outward. The catch: a determinant-1 shear is not a
true rotation, so points trace a slight **ellipse** rather than a circle
(the effective angle isn't exactly Δθ), and on the 6502 the per-step
integer rounding accumulates a slow **shape distortion** over thousands of
frames.

**Use when** the rotation speed is constant and you want minimal code/RAM
and can tolerate a slight, slowly-drifting ellipse. Re-seed the coordinates
periodically, or use method A/B, if you need an exact, non-distorting
rotation — those rebuild from an absolute angle each frame and never drift.

## 5. Animating the angles

Keep an **angle accumulator per axis** and add a constant each frame:

```asm
        clc
        lda angleX
        adc #3               ; pitch speed
        sta angleX
        ; angleY += 4 ; angleZ += 2 ...
```

- Use **different, mutually non-dividing deltas** per axis (e.g. 2/3/4) so
  the combined motion takes a long time to repeat — the object tumbles
  instead of spinning about one axis.
- To change animation phase (speed up, reverse, hold), **self-modify the
  delta immediates**: a small state routine pokes new values into the
  `adc #n` operands. This is a cheap, data-free way to sequence motion.
- Because angles are bytes, they wrap at 256 automatically — no clamping.

## 6. Choosing a rotation method

| Vertices/frame | Method | Why |
|---|---|---|
| a handful | A (matrix, live) | build is cheap, per-vertex cost tolerable, mesh-agnostic |
| dozens–hundreds | B (per-frame LUTs) | build amortized; zero multiplies per vertex |
| fixed spin, tiny code | C (incremental) | no trig, minimal RAM; accepts drift |

> D flag must be clear (`CLD`) at every multiply/interpolation call site;
> the `SMult8`/`SBC` sequences are incompatible with decimal mode.

## See also

- `math.md` — the fixed-point formats, quarter-square multiply and sine these steps call.
- `projection.md` — turning rotated vertices into screen coordinates.
- `rasterizer.md` — turning projected vertices into filled pixels.
- `culling-depth.md` — culling that reuses the rotated normal.
