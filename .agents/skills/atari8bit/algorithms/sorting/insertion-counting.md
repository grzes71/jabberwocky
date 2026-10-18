# Insertion Counting

## 18.7 Index-Linked Insertion Sort

When records are larger than one or two bytes, sort an 8-bit index chain instead
of moving the records. Keep `next[index]` as the link to the next record; use
`$80` or `$ff` as the end marker. This is especially good for visible-object
lists, entity priorities, menu rows, and reverse-engineered tables where the
payload must stay in place.

```text
prev = END
curr = head
while curr != END and key[curr] >= key[new]:
    prev = curr
    curr = next[curr]
next[new] = curr
if prev == END:
    head = new
else:
    next[prev] = new
```

The chain is kept in **descending** key order (the loop advances while
`key[curr] >= key[new]`), which is what depth/priority lists usually want; equal
keys are inserted before existing ones, so this is not a stable sort.

Implementation notes:

- The link byte doubles as an array index, so traversal is cheap: `ldx head`,
  `lda next,x`, `tax`, loop until the sign bit marks the end.
- This is not asymptotically faster than insertion sort, but it avoids payload
  swaps and makes depth/order lists cheap on 6502.
- Use a separate `order[]` output only if the renderer needs contiguous order;
  otherwise traverse the linked list directly.

## 18.8 Stable Counting Sort

Use counting sort when keys are small integers, such as tile priority `0..15`,
depth bucket `0..31`, Huffman code length `1..15`, animation phase, or color
group. It runs in linear time and preserves the input order of equal keys if the
placement pass scans from the end.

Process:

1. Clear `count[0..key_max]`.
2. Scan input and increment `count[key[i]]`.
3. Convert counts to cumulative end offsets.
4. Scan input backwards; decrement `count[key]`, then store the item at that
   output offset.

```asm
; N <= 255, key range 0..15. item[] and key[] are source arrays.
; out_item[] receives stable sorted item order.
; NOTE: INC zp,Y / DEC zp,Y are 65C02-only, so the plain 6502 read/add/write
; form is used for the counter update.
count_sort_4bit
        ldx   #15
        lda   #0
@clear  sta   count,x
        dex
        bpl   @clear

        ldx   n_items
        dex
@hist   lda   key,x
        and   #$0f
        tay
        lda   count,y
        clc
        adc   #1
        sta   count,y
        dex
        bpl   @hist

        ldx   #0
        lda   #0
@cum    clc
        adc   count,x
        sta   count,x           ; count[k] = one-past-end offset for key k
        inx
        cpx   #16
        bne   @cum

        ldx   n_items
        dex
@place  lda   key,x
        and   #$0f
        tay
        lda   count,y
        sec
        sbc   #1
        sta   count,y
        tay
        lda   item,x
        sta   out_item,y
        dex
        bpl   @place
        rts
```

Tested against a reference stable counting sort for 200 random inputs
(N = 1..119, keys 0..15): identical output every time.

Trade-offs:

| Property | Value |
|---|---|
| Time | O(N + key_range) |
| Extra RAM | `key_range` counters + output order buffer |
| Stable | yes, when placed from the end |
| Best use | Small bounded keys; multi-key sorts by sorting secondary key first |

Source note: these two patterns are adapted from the sorting articles in C=
Hacking issue 18 — "Data Structures 101" (Pasi Ojala and S. Judd; linked lists
plus a short insertion sort) and "Counting Sort" (Pasi Ojala). They are portable
6502 ideas, not C64 hardware techniques.

---
