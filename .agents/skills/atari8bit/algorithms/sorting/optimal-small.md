# Optimal Small

## 18.1 Optimal Sort — Small N (8-bit Elements)

For N up to about 8 the cheapest sort is a **sorting network**: a fixed sequence
of compare-exchange operations with no loop counter, no branches per pass and no
recursion. The minimum number of comparators needed is known:

| N | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| comparators | 1 | 3 | 5 | 9 | 12 | 16 | 19 |

A 5-element network using the optimal 9 comparators (checked here against every
zero-one input and on the 6502, where it sorted 400 random cases):

```text
(0,1) (3,4) (2,4) (2,3) (1,4) (0,3) (0,2) (1,3) (1,2)
```

Each pair is one compare-exchange. Written inline for two zero-page operands:

```asm
; CE v1,v2 — order the pair so that v1 <= v2
; 15 bytes: 9 cycles when already ordered, 20 cycles when it has to swap
        lda   v1
        cmp   v2
        bcc   @ce_ok
        ldx   v1
        lda   v2
        sta   v1
        stx   v2
@ce_ok
```

Repeat that block once per comparator; give each instance its own local label or
wrap it in a MADS macro. Because the network works on values, the array is in
place when the last comparator finishes — there is no index list to walk.

For reusable code instead of inlining, a pointer-based compare-exchange is 27
bytes and costs 29 cycles when ordered / 46 when it swaps:

```asm
; p1, p2 = zero-page pointers to the two bytes
cx      ldy   #0
        lda   (p1),y
        sta   ta
        lda   (p2),y
        sta   tb
        lda   ta
        cmp   tb
        bcc   @cx
        beq   @cx
        lda   tb
        sta   (p1),y
        lda   ta
        sta   (p2),y
@cx     rts
```

| | |
|---|---|
| Workspace | none beyond the array (or `p1`/`p2`/`ta`/`tb` for the reusable CE) |
| Key size | 8-bit unsigned (16-bit needs two-byte compares per CE) |
| Comparators | 1/3/5/9/12/16/19 for N = 2..8 (minimum-size networks) |
| Stable | no — compare-exchange can reorder equal keys |

---

## 18.2 Optimal Sort — Larger N (index / link chain)

Past N = 8 the comparator count grows quickly (N = 9 needs 25, N = 10 needs 29),
so switch to an index-linked insertion: keep `next[index]` as the link to the
next record and insert each new index into the chain, as described in §18.7.
Nothing in the payload moves, which is what matters when records are wider than
their keys.

For 16-bit keys, compare the high byte first and only then the low byte; a
16-bit compare-exchange is the 8-bit CE above extended with a second byte, or a
`CMP`/`SBC` pair on `hi`/`lo`. Avoid the temptation to build "6N cycle"
estimates: an insertion-style chain costs O(N^2) comparisons for random input,
and only the constant factors are under your control.

---
