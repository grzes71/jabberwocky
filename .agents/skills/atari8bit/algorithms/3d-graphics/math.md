# 3D math on a machine with no multiply and no divide

> **Load when:** you need the arithmetic primitives — multiply, divide,
> sine — that every transform, projection, interpolation and lighting step
> depends on. Start here; the other 3D topics assume these exist.

The whole subtree rests on one fact: on the 6502 you *precompute*
arithmetic into tables and reduce runtime to `lda table,x`. A software
multiply is ~100–250 cycles; a table lookup is 4–5. Over thousands of
operations per frame that is the difference between a slideshow and
animation.

## 1. Number formats — fixed point

There is no floating point. Represent fractional values as **fixed-point
integers**: a value `v` is stored as `round(v · 2^f)` and you track the
binary point `f` yourself.

Common choices for 3D:

| Format | Bits | Meaning | Range | Use |
|---|---|---|---|---|
| signed byte (Q0) | 8 | integer −128..127 | ±127 | screen coords, small counters |
| **Q3.9** (12-bit value, held in a 16-bit word) | 3 int (incl. sign) + 9 frac | value·512 | −4.0 … +3.998 | matrix elements, unit-scaled coords |
| **8.8** (16-bit) | 8 int + 8 frac | value·256 | 0..255.996 unsigned (−128…+127.996 signed) | interpolation accumulators, slopes |
| Q1.7 (byte) | 1 int + 7 frac | value·128 | −1.0 … +0.992 | normals, cos/sin as a unit fraction |

**Why these.** Matrix elements and rotated coordinates live in roughly
±1..±4, so Q3.9 keeps precision without overflow; after a product you
shift right by the fractional count to renormalize (e.g. two Q1.7 values
multiplied give Q2.14 → `>>7` restores Q1.7-ish). Interpolators want an
8.8 accumulator so the integer part is the top byte you read directly and
the low byte carries the fraction. Pick the smallest format that holds
your range — every extra byte is extra cycles.

**Binary angles.** Store an angle as a single byte where `0..255` spans a
full turn (256 "brads"). Rotating by adding to the angle then wraps for
free (byte overflow = 360°), and the angle indexes a 256-entry trig table
directly. This is why 3D code almost never uses degrees or radians.

**Decimal-mode hazard.** All of this uses binary `ADC`/`SBC`. Ensure the
D flag is clear (`CLD`) before any multiply/interpolation; a stray `SED`
corrupts every add. Interrupt handlers must `CLD` on entry if they do
arithmetic.

## 2. Multiply — the quarter-square method

You will multiply constantly (matrix × vertex, coordinate scaling). The
naive shift-add multiply is a loop of 8 `ASL`/`ADC` — correct but ~150+
cycles. The standard fast method is **quarter-square**:

```
a·b = f(a+b) − f(a−b)   where   f(x) = x² / 4
```

Precompute `f(x) = floor(x²/4)` once. Then a multiply is two table
lookups and a subtract. Because `a+b` can reach 510, `f` needs 512
entries; store it as two 512-byte tables `SQR_LO`, `SQR_HI` (the 16-bit
square split into low/high bytes), **page-aligned**.

### Unsigned 8×8 → 16 (~54 cycles)

Self-modify the table base with one operand so the other indexes it:

```asm
; in:  ma, mb (0..255)     out: prod_lo/prod_hi
UMult8  lda ma
        sta getLo+1          ; patch: SQR_LO + ma  (page-aligned base)
        sta getHi+1
        ldx mb               ; X = the other operand
        sec
        sbc mb               ; A = ma-mb  (may borrow)
        bcs @+               ; carry-preserving |ma-mb|:
        sbc #0               ;   C=0 -> A=A-1, and sets C=1
        eor #$FF             ;   A = mb-ma
@       tay                  ; Y = |ma-mb|, C=1 guaranteed
getLo   lda SQR_LO,x         ; patched -> SQR_LO[ma+mb]
        sbc SQR_LO,y
        sta prod_lo
getHi   lda SQR_HI,x
        sbc SQR_HI,y
        sta prod_hi
        rts
```

The `bcs/sbc #0/eor` idiom computes `|ma−mb|` while *leaving carry set*,
so the 16-bit subtraction below needs no `SEC` — a small but real saving
repeated thousands of times.

### Signed 8×8 → 16 (~98 cycles)

Take absolute values, multiply as unsigned, then negate the result if the
signs differed:

```asm
SMult8  lda ma
        eor mb
        sta sign             ; bit7 = result sign
        ; ma = |ma|, mb = |mb|  (bpl/eor #$FF/adc #1 on each)
        ; ... then UMult8-style f(|a|+|b|) - f(||a|-|b||) ...
        ; finally: if sign bit7 set, negate prod (eor #$FF / adc #1, 16-bit)
        rts
```

**Why quarter-square over shift-add:** ~2–3× faster and near-constant-time
(one ~3-cycle data-dependent branch in the |a−b| setup, versus the
shift-add's eight; the table work itself is branchless), at a cost of 1 KB
of tables. On a cycle-starved renderer that trade is almost always right.
Use shift-add only when RAM is scarce or a multiply is rare.

**Why not a full 256×256 product table:** it would be 64 KB — impossible.
Quarter-square gets full 8×8 coverage from 1 KB.

## 3. Divide and reciprocal — tables again

Division shows up in **perspective** (`screen = coord·focal / z`) and in
**interpolation slopes** (`step = Δ / count`). Software division is even
slower than multiply, so tabulate it.

### Small reciprocal table (perspective by z)

If you only ever divide by a bounded depth `z`, precompute the *scaled
reciprocal*:

```
RECIP[z] = round(FOCAL · 256 / z)     for z = ZMIN .. 255
```

Then `screen = (coord · RECIP[z]) >> 8` — one multiply + a lookup, no
divide. One entry per byte (256 bytes) is only valid while
`FOCAL · 256 / z ≤ 255`, i.e. `z ≥ ZMIN = ceil(FOCAL·256 / 255)`
(≈ `FOCAL` while `FOCAL ≤ 255`). `z = 0` is undefined and `z < ZMIN`
overflows the byte, so clamp the depth to `ZMIN..255` — choose `CAM_DIST`
so the nearest visible depth is already ≥ `ZMIN` — or keep 16-bit entries
if you really must divide by small depths.

### General fixed-point divide table (interpolation slopes)

When you need `Δ / count` for arbitrary small `Δ` and `count`, a 2-D
table indexed by (numerator-high, divisor) gives the fixed-point quotient
directly:

```
DIV[n][d] = lowbyte( n·256 / d )      n = 0..63,  d = 1..127
```

Lay it out as rows of 256 bytes, page-aligned, so `base = DIV + (n<<8)`
and `lda (base),y` with `y = d` returns the 8.8 quotient's low byte. This
turns "spread a delta of `n` over `d` pixels" into one load — exactly the
per-pixel step a Gouraud ramp or texture walk needs.

```asm
; step = (n<<8)/d, n in A (0..63), d in Y (1..127)
        clc
        adc #>DIV_TABLE      ; page of numerator n (table page-aligned)
        sta ptr+1
        lda #0
        sta ptr
        lda (ptr),y          ; = lowbyte(n*256/d)
```

The low byte holds the **fractional 8.8 step** — right for interpolation,
where the delta is smaller than the span (`n < d`), so the step is < 1 and
the integer part is 0. When `n ≥ d` (step ≥ 1) you also need the integer
part; track it separately or add a high-byte table.

**Sizing.** A 64×256 table is 16 KB — large, but shared across every
division in the renderer and independent of the content being drawn. Use
the small 256-byte `RECIP` when a single divisor axis (depth) is all you
need; use the 2-D table when you also interpolate shade/texture/edges. It
is the classic space-vs-time call: 16 KB of ROM buys you divide-free
interpolation.

**Why a divide table beats iterative division here:** the values are
small and bounded, lookups are constant-time, and you do the divide in
the innermost loop where a ~200-cycle software divide would dominate the
frame.

## 4. Sine and cosine — quarter-wave storage

Rotation needs `sin`/`cos` of a binary angle. A full 256-entry signed
sine table is only 256 bytes, so you *can* just store it. But two space
savers are common and worth knowing:

### Quarter-wave + quadrant folding

A sine wave has four-fold symmetry. Split the angle into a quadrant
(top two bits) and a position within it (bottom six bits):

- **bit 6** (quadrants 1 and 3): **mirror** the index → `63 − pos`;
- **bit 7** (quadrants 2 and 3): **negate** the result.

Store only the first quarter (64 entries) and reconstruct:

```asm
; A = angle 0..255  ->  A = sin(angle) as a signed byte.
; QSIN = 64-entry quarter wave (index 0..63 spans 0..~90 degrees).
sine    sta ang             ; keep the angle for the quadrant tests
        and #$3F            ; pos = angle mod 64 (position in quadrant)
        tax                 ; assume no mirror (quadrants 0 and 2)
        lda ang
        and #$40            ; bit 6 -> quadrants 1 and 3: mirror
        beq @+
        txa
        eor #$3F            ; index = 63 - pos
        tax
@       lda QSIN,x
        bit ang             ; bit 7 -> quadrants 2 and 3: negate
        bpl @+
        eor #$FF
        clc
        adc #1
@       rts
```

`cos(a) = sin(a + 64)` — no separate cosine table; just offset the index
by a quarter turn.

The `63 − pos` mirror is one brad short of a full 256-entry table (worst
case ≈4 LSB at amplitude 127, near the low end of a quadrant); store 65
entries (`0..64`) and mirror with `64 − pos` when the fold has to be exact.

> **Common mistake:** mirroring whenever the angle is ≥ 64 (a `cpy #$40`
> test) instead of only when bit 6 is set. That wrongly mirrors quadrant 2,
> so `sin(180°)` comes out near −max instead of 0. Mirror on **bit 6**,
> negate on **bit 7** — they are independent.

**Why fold:** saves ~192 bytes and, more importantly, lets you generate
the table trivially at build time. **Why *not* fold:** the folding costs
~35 cycles per call (measured; a bare 256-entry `lda table,x` is 4); if you
call it in a hot loop, store the full 256 entries (and even a full `cos`)
and pay bytes instead of cycles. Typical
choice: fold when building per-frame rotation tables (called ~9 times a
frame); full table when indexing per vertex.

### Amplitude-scaled tables

If every use multiplies `sin` by the same radius, bake it in: store
`R·sin(a)` so the vertex loop skips a multiply. One table per distinct
radius. Trades a little ROM for a multiply removed from the inner loop.

## 5. Square root and distance

Needed for normalizing, shading falloff, or distance culling.

- **Table** for 8-bit inputs: `ISQRT[x] = round(sqrt(x))`, 256 bytes —
  the fastest.
- For 16-bit inputs, a Newton step or the classic "subtract successive
  odd numbers" integer sqrt; see `algorithms/math.md`.
- Distance without sqrt: compare *squared* distances (using the square
  table above) when you only need ordering, not the actual length — this
  is the trick behind distance culling and depth keys.

## 6. Practical rules

- **Page-align every table you index by a modified base byte.** Quarter-
  square and the divide table both patch the low byte of an address or add
  to the high byte; alignment makes `base + index` correct without
  carry handling.
- **Keep hot tables in RAM or fast ROM**, ideally in a region you can
  reach with zero-page indirect addressing for the innermost loops.
- **Renormalize immediately after each product** (`>>f`) so intermediate
  values stay in byte range and you never carry a stale scale factor.
- **Budget by counting lookups, not instructions.** A transform that is
  "all table lookups" is your target; any remaining software multiply in
  an inner loop is the first thing to tabulate away.
- **Generate the tables at build time, never by hand.** MADS evaluates
  expressions at assembly time, so you can emit a table with a directive —
  e.g. a page-aligned signed sine as `dta b(sin(0,127,256))` (MADS is
  `sin(centre,amp,size)`, so this is 256 bytes of `127·sin`), or a
  square/reciprocal table with a `.rept` loop — and regenerate it whenever
  a parameter changes. See `algorithms/math/trig-tables.md` for the sine
  form and `tooling/mads-assembler.md` for the expression syntax.

## See also

- `rotation.md`/`projection.md` — how these primitives compose into rotation/projection.
- `rasterizer.md` — where the divide table feeds interpolation slopes.
- `algorithms/math.md` — general-purpose multiply/divide/sqrt listings.
