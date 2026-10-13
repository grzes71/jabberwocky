# Bucket Depth

## 18.3 Bucket Sort — 3D Depth Order

An 8-way bucket sort is the usual pick for the ~50–100 visible faces of a
filled-3D object. Depth keys are 0–255 unsigned bytes, so the bucket index
is `depth >> 5` (256 / 8 = 32 depth units per bucket). Zero comparisons.

> The shift must match the bucket count: `>> 5` gives 8 buckets, `>> 3`
> would give 32. Using `>> 3` with only 8 bucket heads (below) silently
> drops the faces that land in buckets 8..31 — a classic mistake.

```asm
SortVisible
        ldx    #$07
        lda    #$00
@clear  sta    BKT_HEAD,x      ; one loop clears all 8 heads
        dex
        bpl    @clear

@fill   lda    BUF_DEPTH,x
        lsr                   ; depth >> 5  -> bucket 0..7
        lsr
        lsr
        lsr
        lsr
        tay
        lda    bkt_head,y     ; current bucket head
        sta    next,x          ; link this face to it
        txa                    ; (or lda vis_quad,x if the chain must store a face id)
        sta    bkt_head,y     ; push into bucket
        inx
        cpx    vis_count
        bne    @fill

        ; Drain bucket 7 (far) to bucket 0 (near) by walking each chain
        ldy    #$07
@bucket lda    bkt_head,y
        beq    @next
        ; follow next[] chain into the sorted output array
@next   dey
        bpl    @bucket
```

Do not try to clear the heads with `sta bkt_0..bkt_7`: MADS does not accept an
address range as an instruction operand.

| | |
|---|---|
| Buckets | 8 (depth >> 5) |
| Bucket storage | BKT_HEAD[8], zero page |
| Link storage | NXT_PTR[96] |
| Cycles | ~3.9 K for the clear plus one pass over 96 faces (~40 cycles/face, measured) |
| Key comparisons | 0 |

---
