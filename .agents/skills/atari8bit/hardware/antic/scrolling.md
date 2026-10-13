# Scrolling

## 3.3  Scrolling — Coarse & Fine (2D, Hardware-Accelerated)

### 3.3.1 Vertical coarse scrolling

Keep the VS bit set on each mode line in the scrolling region. When `VSCROL`
wraps, move the **first LMS address** of the region by one logical row.

```asm
; Scroll viewport DOWN one row in a 40-byte-wide region
coarse_scroll_down
        clc
        lda dlist_lms          ; low byte first
        adc #40
        sta dlist_lms
        lda dlist_lms+1
        adc #0
        sta dlist_lms+1
        rts
```

**Scroll direction vs. memory direction:**

| Action | User sees | LMS address move |
|---|---|---|
| Scroll **down** | content rises | add bytes/row |
| Scroll **up** | content falls | subtract bytes/row |

### 3.3.2 Vertical fine scrolling (`VSCROL`)

`VSCROL` (`$D405`) is measured in **scan lines**, not pixels. Valid values are
0 through the mode-line height minus 1.

```asm
vert_scroll      = $90
vert_scroll_max  = 8         ; Mode 4 = 8 scan lines per row

fine_scroll_down
        inc vert_scroll
        lda vert_scroll
        cmp #vert_scroll_max
        bcc ?done
        jsr coarse_scroll_down
        lda #0
        sta vert_scroll
?done   sta VSCROL
        rts
```

For reliable splits, update `VSCROL` either in VBI or immediately after
`WSYNC` in a DLI.

### 3.3.3 Horizontal coarse scrolling

Horizontal coarse scroll changes the LMS address for each visible row.
With a normal linear screen buffer, that means shifting the start address of
all rows by **one byte per coarse step**. In a page-per-line layout, you usually
adjust the low byte of each LMS independently.

```asm
; Scroll all 22 LMS addresses one byte left in a page-per-line layout
coarse_scroll_left
        ldy #22
        ldx #4
?loop   dec dlist_lms_mode4,x
        inx
        inx
        inx
        dey
        bne ?loop
        rts
```

### 3.3.4 Horizontal fine scrolling (`HSCROL`)

`HSCROL` (`$D404`) shifts the display by 0–15 color clocks. Only the low 4 bits
matter.

```asm
horz_scroll      = $91
horz_scroll_max  = 4       ; Mode 4 = 4 color clocks per character

fine_scroll_left
        inc horz_scroll
        lda horz_scroll
        cmp #horz_scroll_max
        bcc ?done
        jsr coarse_scroll_left
        lda #0
        sta horz_scroll
?done   sta HSCROL
        rts
```

**HSCROL rules:**

| Rule | Explanation |
|---|---|
| Narrow/normal fetch one width larger | ANTIC fetches extra data as the scroll buffer |
| Wide playfield has no wider buffer | use wide DMA explicitly if you need wide + scroll |
| GTIA 9/10/11 | use **even** HSCROL values so GTIA pixel pairing stays correct |
| Mid-line changes | safe updates belong in HBLANK / `WSYNC`, not in active display |

### 3.3.5 Combined 2D scrolling

Typical pattern:

1. Update `HSCROL`/`VSCROL` once per frame.
2. When a fine scroll wraps, perform the corresponding coarse LMS update.
3. Precompute new row/column data off-screen or in the buffer line.
4. Use a DLI only when different screen bands need different scroll values.
