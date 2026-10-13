# Selection

## 18.6 Selection Guide

```
N <= 8          ->  Sorting network (fixed comparator sequence, no loop)
N < 20          ->  Index-linked insertion (no payload moves)
N = 50-200      ->  Bucket sort 8-way        (zero comparisons)
N large/unsorted->  Quicksort 16-bit          (median-of-3 pivot, network for small tails)
Nearly sorted   ->  CombSort                  (gap=1 only on last pass)
Tiny code       ->  ShellSort Hibbard         (small; needs no ZP workspace beyond the entries)
```

---
