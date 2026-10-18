# Atan2 Log

## 10.9 Logarithmic atan2 (log-ratio + octant adjust)

The useful identity is **not** `atan2(dy,dx) = log2(|dy|) - log2(|dx|)`.
Instead, the difference of logarithms is used as a compact way to approximate
the ratio `min/max`, and that ratio then indexes an `atan` lookup table.

Typical flow:

1. Compute `dx` and `dy`.
2. Take absolute values and handle the axis cases (`dx=0` or `dy=0`) directly.
3. Let `major = max(|dx|,|dy|)` and `minor = min(|dx|,|dy|)`.
4. Form `d = log2(major) - log2(minor)`.
5. Look up the first-octant angle from `atan_tab[d]`.
6. Map that angle back into the correct octant/quadrant from the original sign
   bits and from whether `|dy| > |dx|`.

This is fast because it replaces a general divide with two LUT reads, one
subtraction, and an octant remap, but it is still an approximation whose error
depends on the chosen `log` and `atan` tables.

---
