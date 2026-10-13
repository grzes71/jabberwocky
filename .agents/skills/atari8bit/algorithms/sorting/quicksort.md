# Quicksort

## 18.4 Quicksort — 16-bit Keys

In-place partition, then recurse on the two halves. The parts that matter on a
6502:

- Compare 16-bit keys high byte first, and only compare the low byte when the
  high bytes are equal.
- Keep the current `lo`/`hi` bounds in zero page and pass the range through the
  stack (`PHA` high byte first, then low byte) so the routine stays re-entrant
  and each level costs only the pushed pair.
- Recursion depth is the real hazard: a bad pivot can need O(N) levels, which
  eats the 256-byte stack. Push the bounds explicitly and loop on the larger half
  (recursing only into the smaller one), or cap the depth.
- Complexity: O(N log N) comparisons on average, O(N^2) worst case — already
  sorted or reverse-sorted input with a first/last pivot is the classic failure.
- Stop recursing below about 8 elements and finish with the sorting network from
  §18.1; this removes most of the call overhead for small partitions and avoids
  the "quicksort a tiny range" pathology.

> A median-of-3 pivot (two extra compares per partition) removes the classic
> sorted-input worst case, but it is a guard, not a guarantee: an adversary can
> still make median-of-3 pick an extreme element.

---
