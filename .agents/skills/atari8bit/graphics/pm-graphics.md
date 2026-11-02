---
name: atari8bit-pm-graphics
description: >-
  Atari player/missile graphics: PMG memory layout, DMA enable sequence, GTIA
  position/size/priority registers, collisions, movement, and DLI multiplexing.
---

# Player/Missile Graphics

> **Scope:** Atari hardware players and missiles, PMG memory, GTIA registers, priority, size, movement, and collisions.
> **Do not use for:** CPU-rendered software sprites; use `graphics/software-sprites.md`.

## Quick-Lookup

| Need | See |
|---|---|
| PMG memory layout | §1 |
| Enable sequence | §2 |
| Move players/missiles | §3 |
| Colors, sizes, priority | §4 |
| Collision registers | §5 |
| DLI multiplexing | §6 |

## §1 PMG Memory Layout

PMG data is fetched by ANTIC DMA from the base selected by `PMBASE ($D407)`.
The value written to `PMBASE` is the high byte of the PMG area.

Resolution is selected by `DMACTL` bit 4:

| Mode | `DMACTL` bit 4 | Required alignment | Bytes per player | Notes |
|---|---:|---:|---:|---|
| Double-line | 0 | 1 KB | 128 | One PMG byte covers two scan lines |
| Single-line | 1 | 2 KB | 256 | One PMG byte covers one scan line |

Common offsets from the PMG base:

| Object | Offset |
|---|---:|
| Missiles 0-3 (shared area) | `$0300` |
| Player 0 | `$0400` |
| Player 1 | `$0500` |
| Player 2 | `$0600` |
| Player 3 | `$0700` |

## §2 Enable Sequence

Two chips participate:

- `DMACTL ($D400)` enables ANTIC fetching of missile/player data.
- `GRACTL ($D01D)` enables GTIA display of the fetched graphics.

Useful bits:

| Register | Bit | Meaning |
|---|---:|---|
| `DMACTL` | 2 | Missile DMA |
| `DMACTL` | 3 | Player DMA |
| `DMACTL` | 4 | Single-line PMG resolution |
| `DMACTL` | 5 | Display-list DMA |
| `GRACTL` | 0 | Missile display enable |
| `GRACTL` | 1 | Player display enable |
| `GRACTL` | 2 | Trigger latch enable |

```asm
pm_base_page = >pm_area

init_pmg
        lda   #0
        sta   GRACTL

        lda   #pm_base_page
        sta   PMBASE

        lda   #0
        ldx   #0
?clear  sta   pm_area,x
        sta   pm_area+$100,x
        sta   pm_area+$200,x
        sta   pm_area+$300,x
        sta   pm_area+$400,x
        sta   pm_area+$500,x
        sta   pm_area+$600,x
        sta   pm_area+$700,x
        inx
        bne   ?clear

        lda   #%00111110      ; normal PF + DL DMA + single-line PMG + players + missiles
        sta   DMACTL
        lda   #%00000011      ; show missiles + players
        sta   GRACTL
        lda   #$00
        sta   HITCLR
        rts
```

If the OS is active, write the OS shadow `SDMCTL ($022F)` instead of only
`DMACTL`; the OS VBI copies `SDMCTL` back to hardware.

## §3 Move Players and Missiles

Vertical movement is a memory copy into the object's PMG lane. To avoid trails,
erase the old span before copying the new one.

```asm
erase_player0
        ldx   old_vpos
        lda   #0
        ldy   #sprite_h
?clr    sta   pm_area+$0400,x
        inx
        dey
        bne   ?clr
        rts

draw_player0
        ldx   new_vpos
        ldy   #0
?copy   lda   (src),y
        sta   pm_area+$0400,x
        inx
        iny
        cpy   #sprite_h
        bne   ?copy

        lda   hpos
        sta   HPOSP0
        lda   new_vpos
        sta   old_vpos
        rts
```

Horizontal position registers:

| Register | Address | Object |
|---|---:|---|
| `HPOSP0`-`HPOSP3` | `$D000-$D003` | Players |
| `HPOSM0`-`HPOSM3` | `$D004-$D007` | Missiles |

## §4 Colors, Sizes, and Priority

| Register | Address | Purpose |
|---|---:|---|
| `PCOLOR0`-`PCOLOR3` | `$02C0-$02C3` | OS shadows for player/missile colors |
| `COLPM0`-`COLPM3` | `$D012-$D015` | Hardware colors; write in a DLI for same-line changes |
| `SIZEP0`-`SIZEP3` | `$D008-$D00B` | Player horizontal size |
| `SIZEM` | `$D00C` | Two bits per missile size |
| `PRIOR` | `$D01B` | Priority, fifth-player mode, player-overlap mode, GTIA modes |

Player size values are:

- `0` = normal
- `1` = double width
- `2` = same as normal
- `3` = quadruple width

`SIZEM` packs four 2-bit missile sizes:

```asm
; missile 0 normal, missile 1 double, missile 2 quad, missile 3 normal
        lda   #%00110100
        sta   SIZEM
```

Priority notes:

- `PRIOR` bits 0-3 choose the player/playfield layering scheme
- bit 4 converts missiles into a fifth player using `COLPF3`
- bit 5 enables OR-colour mixing where players overlap
- bits 6-7 select GTIA modes 9/10/11

Use `PCOLOR0-3`/`GPRIOR` in ordinary frame code when the OS is active. Use
`COLPM0-3`/`PRIOR` directly inside a DLI when the change must affect the
current frame immediately.

## §5 Collision Registers

PMG collision latches remain set until `HITCLR ($D01E)` is written.

| Range | Purpose |
|---|---|
| `$D000-$D003` read | Missile-to-playfield collisions |
| `$D004-$D007` read | Player-to-playfield collisions |
| `$D008-$D00B` read | Missile-to-player collisions |
| `$D00C-$D00F` read | Player-to-player collisions |

```asm
read_collision
        lda   P0PF            ; player 0 vs PF0-PF3 pixels
        bne   ?hit
        rts
?hit    lda   #$00
        sta   HITCLR
        rts
```

## §6 DLI Multiplexing

Hardware gives four players and four missiles, but a DLI can reuse them in
separate vertical bands by changing `HPOSPn`, `SIZEPn`, `COLPMn`, `PRIOR`, or
the PMG data itself before the next band is drawn.

Rules:

- Precompute tables in VBI; keep DLI work to loads and stores.
- Use `WSYNC` when a change must land cleanly on the next scan line.
- Leave some vertical separation between reused bands unless the kernel timing
  is already proven.
- If another subsystem owns `VDSLST`, centralize DLI ownership instead of
  installing competing handlers.

For CPU-rendered sprite engines that combine with PMG overlays, keep PMG for
small high-priority objects and use `graphics/software-sprites.md` for the
background sprite layer.

## §7 Scanline Coordinate Mapping & Color Table Architecture

### Display List to PMG Memory Offset Formula

When using single-line PMG resolution (`DMACTL` bit 4 = 1), ANTIC DMA fetches from the PMG buffer starting immediately after vertical blank.
If a custom display list has $B$ blank scanlines at the top (e.g. 3x `DL_BLANK8` = 24 scanlines) before playfield line 0:
$$\text{PMG Buffer Offset} = \text{TopBlankScanlines} + \text{VBLANK\_End\_Scanline} + (Y \times \text{ScanlinesPerModeLine})$$
In typical Atari 8-bit setups (VBLANK ending at scanline 8, with 24 top blank scanlines, display line 0 starts at TV scanline 32):
- Mode D line $Y$ (2 scanlines/line): $\text{Offset} = 32 + (Y \times 2)$.
- Guard lines and unallocated bands in PMG memory must remain cleared to `$00` to prevent ghost stripes when multiplexing registers.

### Unified Color Table Optimization

If multiple PMG channels share identical per-scanline color profiles (such as 3 players forming a composite multi-segment platform, along with 4 missiles converted to a 5th player via `PRIOR` bit 4):
- Do **not** generate separate tables for each channel (`pas_c1_sl`, `pas_c2_sl`, etc.).
- Generate **one single unified color table** (`pas_color_sl0..7`).
- In the inner DLI scanline loop, perform a single `LDA` from the shared table and write it to all participating channels:
  ```asm
  lda dli_pas_color_slN,y   ; [4] Single load for all channels
  sta COLPM1                ; [4]
  sta COLPM2                ; [4]
  sta COLPM3                ; [4]
  sta COLPF3                ; [4] 5th player / missiles
  sta WSYNC                 ; [4]
  ```
- **Benefits:**
  - Saves 66% of color table ROM and double-buffer RAM ($24 \to 8$ tables per zone).
  - Saves 8–12 CPU cycles per scanline in time-critical display kernels.

