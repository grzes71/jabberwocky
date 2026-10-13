# Comb Shell

## 18.5 CombSort + ShellSort

### CombSort (gap-based bubble sort)

Gap sequence: `N`, `N/1.3`, `N/1.3^2`, ... down to 1. Each pass compares pairs
`gap` apart and swaps them when they are out of order; once a pass with `gap = 1`
makes no swap, the array is sorted.

- The shrink factor is 1.3, so the integer form is `gap = gap * 10 / 13`
  (`10/13 = 0.769 = 1/1.3`). On 6502: widen the gap to 16 bits, multiply by 10
  (shift/add), then divide by 13; rounding down is fine because the loop clamps
  the gap to a minimum of 1.
- Worst case is O(N^2), the same bound as bubble sort. What makes it usable is
  that the number of gap passes grows only logarithmically with N, so the big
  early passes do most of the work.
- Not stable.

### ShellSort (insertion sort over decreasing gaps)

ShellSort is an insertion sort repeated with a shrinking gap; the gap sequence is
the only real choice:

- Knuth `3h+1`: `1, 4, 13, 40, 121, 364, 1093, 3280, 9841`. This is the sequence
  used by the MADS example `examples/math/shell_sort.asm`, which sorts 16-bit
  elements and therefore doubles the table: `2, 8, 26, 80, 242, 728, ...`.
- Hibbard `2^k - 1`: `1, 3, 7, 15, 31, 63, 127, 255`. Fewer gaps, so slightly
  less code and table space.

Both sequences give O(N^1.5) worst-case comparisons, far better than repeated
gap-1 passes. Replacing the inner shift with a straight swap keeps the code
smaller but makes the sort unstable; stopping the shift when the keys are equal
is what preserves stability.

```asm
; gap table for byte elements, largest first (Knuth 3h+1, N <= 128)
gaps    dta   121, 40, 13, 4, 1, 0
```

### Cost summary

| Algorithm | N | Work | Code | Stable? |
|---|---|---|---|---|
| Small-N sorting network | 2..8 | 1/3/5/9/12/16/19 comparators (minimal) | ~15 B per comparator inline | no |
| CombSort | any | O(N^2) worst, `log(N)` gap passes | small | no |
| ShellSort (Knuth / Hibbard) | any | O(N^1.5) worst | small | no |
| Quicksort 16-bit | any | O(N log N) average, O(N^2) worst | medium | no |
| Bucket 8-way | 50–200 | 0 key comparisons, O(N) placement | small | no |

---
