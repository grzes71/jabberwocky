# Player Missile

## §4.6  Player / Missile Graphics (P/M Graphics)

### P/M Memory Layout

PM graphics use a dedicated memory area selected by `PMBASE ($D407)`. The value
written to `PMBASE` is the high byte of the PMG area.

- **Double-line resolution** (`DMACTL` bit 4 clear): PMG base must be **1 KB aligned**.
- **Single-line resolution** (`DMACTL` bit 4 set): PMG base must be **2 KB aligned**.

The standard offsets from `PMBASE` are the same in both resolutions:

| Object | Offset from `PMBASE` | Bytes used |
|---|---:|---:|
| Missiles 0-3 (shared area) | `$0300` | 128 / 256 |
| Player 0 | `$0400` | 128 / 256 |
| Player 1 | `$0500` | 128 / 256 |
| Player 2 | `$0600` | 128 / 256 |
| Player 3 | `$0700` | 128 / 256 |

The smaller byte count is for double-line PMG; the larger is for single-line PMG.

### Enable Path

Two chips participate:

- `DMACTL/SDMCTL` on ANTIC controls **DMA fetch**
- `GRACTL` on GTIA controls **display enable**

Relevant bits:

| Register | Bit | Meaning |
|---|---:|---|
| `DMACTL` | 2 | Missile DMA enable |
| `DMACTL` | 3 | Player DMA enable |
| `DMACTL` | 4 | Single-line PMG when set; double-line when clear |
| `GRACTL` | 0 | Missile display enable |
| `GRACTL` | 1 | Player display enable |
| `GRACTL` | 2 | Trigger-latch enable |

If the OS is active, update `SDMCTL ($022F)` rather than only writing
`DMACTL ($D400)`, or the next VBI will restore the shadow value.

### Graphics Registers

`GRAFP0-3` and `GRAFM` are the live shift-pattern registers used by GTIA.
Normally ANTIC PMG DMA refreshes them every visible scan line from PMG memory.
Without DMA, CPU writes to those registers create vertical bars or borders.

Missiles share one graphics register:

- bits 1-0 = missile 0
- bits 3-2 = missile 1
- bits 5-4 = missile 2
- bits 7-6 = missile 3

### Sizes

Each player has its own size register:

| Value | Player size |
|---|---|
| `$00` | normal |
| `$01` | double |
| `$02` | normal |
| `$03` | quadruple |

`SIZEM` packs four 2-bit missile sizes in the same encoding.

### Priority / Overlap Controls

`PRIOR ($D01B)` combines several unrelated GTIA features:

- bits 0-3: choose one of the hardware player/playfield priority orders
- bit 4: convert the four missiles into a **fifth player** coloured by `COLPF3`
- bit 5: enable **player overlap OR-colour** mixing
- bits 6-7: select GTIA modes 9/10/11

Player overlap colour mixing is not automatic in normal mode; it is enabled by
`PRIOR` bit 5. The fifth-player option is controlled by bit 4, not by the
priority-selection bits.

### VDELAY

`VDELAY ($D01C)` delays selected PMG objects by one scan line. It is mainly
useful with **double-line PMG**, where it lets one object appear vertically
offset by one scan line relative to the others.

### Practical Movement

Vertical movement is done by writing new bytes into the object's PMG lane.
To avoid trails, clear the old span before copying the new span.

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

Horizontal position comes from `HPOSP0-3` for players and `HPOSM0-3` for missiles.

### DLI Multiplexing

You can reuse the same hardware players in separate vertical bands by changing
`HPOS`, `SIZEP`, `COLPM`, `PRIOR`, or even the PMG data in a DLI between bands.

Good practice:

- prepare tables in VBI
- keep DLI work to loads/stores
- use `WSYNC` when a change must take effect cleanly on the next scan line
- centralize ownership if more than one subsystem wants to install DLIs
