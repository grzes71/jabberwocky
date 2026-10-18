# Sqrt Distance

## 10.10 Distance computation (squares + sqrt)

A common 6502 pattern for Euclidean distance is:

```text
dist = floor(sqrt(dx*dx + dy*dy))
```

### Squared tables

For bounded magnitudes, a square table is straightforward and exact:

```asm
squared_table_lo:
        :MAX+1 dta l(#*#)
squared_table_hi:
        :MAX+1 dta h(#*#)
```

That same table is useful for distance checks, radius tests, and some
table-driven multiply variants.

### Exact vs approximate scaling

If you halve `dx` and `dy` before squaring to stay inside a smaller table or a
16-bit accumulator, the final rescaled result is an **approximation**, not an
exact Euclidean distance. That trade-off is fine when the caller wants a cheap
velocity metric, but document it explicitly.

### Square-root choices

- **Binary search over a square table** is exact when the table covers the full
  search range.
- **Restoring / digit-by-digit sqrt** is table-free and exact, but slower.
- **Piecewise / LUT approximations** are often good enough for gameplay and
  animation, but should be labelled as approximations.

---

## 10.12 Fast 16-bit Square Root

Fast table-driven square roots exist, but they are implementation-specific.
Keep the contract explicit: input range, output rounding rule, table size, and
whether the result is exact or approximate.

---
