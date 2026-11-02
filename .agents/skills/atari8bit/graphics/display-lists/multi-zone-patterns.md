# Multi Zone Patterns

## §4  Multi-Zone DLI Patterns

### §4.1  VBI-precomputed band tables + one shared DLI

For split screens where each band needs different colors or scroll values,
compute the per-band values in VBI and let each DLI consume the next table
entry.

```asm
zone_index   = $80
band_colpf0  = $90          ; one byte per zone
band_hscroll = $A0          ; one byte per zone

vbi_setup
        lda #0
        sta zone_index
        lda #<band_dli
        sta VDSLST
        lda #>band_dli
        sta VDSLST+1
        rts

band_dli
        pha
        txa
        pha
        tya
        pha

        ldx zone_index
        sta WSYNC
        lda band_colpf0,x
        sta COLPF0
        lda band_hscroll,x
        sta HSCROL
        inx
        stx zone_index

        pla
        tay
        pla
        tax
        pla
        rti
```

**Design points:**

- Put the DLI bit only on the scan lines where a band change starts.
- Precompute the band tables in VBI or main code, not inside the DLI.
- Write hardware registers (`$D0xx` / `$D4xx`) in the DLI.

### §4.2  Chained handlers when each band needs different code

If bands need different logic, let each DLI install the next handler in
`VDSLST` and let VBI restore the first handler at the top of the frame.

```asm
dli_sky
        pha
        txa
        pha
        tya
        pha

        lda #<dli_ground
        sta VDSLST
        lda #>dli_ground
        sta VDSLST+1

        sta WSYNC
        lda #$88
        sta COLPF0

        pla
        tay
        pla
        tax
        pla
        rti
```

This pattern keeps the DLI bodies short while still allowing per-band changes.

### §4.3  PMG Channel Multiplexing Across Bands & Guard-Line Race Conditions

When hardware player/missile channels (P0..P3, M0..M3) are shared between different visual entities in different vertical screen zones (for example: P1..P3 used as wide platform segments inside a band, and reused as enemy sprites in the guard lines / gaps between bands):

#### The "Ghost Stripe" Hazard
If the DLI kernel transitions between band mode (e.g. platform sizes/positions) and zone mode (enemy sizes/positions/colors):
1. ANTIC DMA fetches PMG pattern data line-by-line continuously.
2. If the handler updates `HPOSP`, `COLPM`, or `SIZEP` for the next zone while the scan beam is still on a scanline where the PMG DMA buffer contains active pattern bits from the previous band (e.g. `$FF`), GTIA will **immediately render a 1-scanline slice** of that pattern at the new `HPOSP` position with the new `COLPM` color!

#### Defensive Rules
1. **Zero-Byte Guard Lines:** Ensure the scanlines immediately following any multiplexed band contain strictly `$00` in PMG memory.
2. **Align Register Commits to Clean Scanlines:** Never update `HPOSP` or `COLPM` until the CPU has crossed into a scanline whose PMG buffer is guaranteed to be `$00`.
3. **Double-Check Multi-Scanline Offsets:** If a multi-scanline mode (e.g. Mode D) starts Faza B even 1 scanline early, the exit phase will commit zone registers 1 scanline early — landing right on the last scanline of the previous band's non-zero PMG data.
4. **Keep each DLI phase within the per-scanline DMA budget:** with playfield + PMG DMA active only ~57 CPU cycles remain usable per Mode D scanline (~70 on a DMA-light repeat scanline). A phase that overruns its scanline pushes the next `STA WSYNC` into the following line and shifts the *whole* kernel one scanline late - the symptom is a colour profile shifted down by one line (the first scanline keeps the previous zone's stale enemy/secret colour). Measured in this project: a 55-cycle setup phase fits, 79 cycles slip. See `hardware/antic/dli-wsync.md` §3.9 and `hardware/antic/dma-timing.md`.
5. **Commit the next band's state in the last pre-band scanline:** since a PMG register write is only visible from the *following* scanline (`hardware/gtia/player-missile.md`, "When a PMG Register Write Takes Effect"), the last scanline before the band is both the earliest and the latest safe commit point. Earlier and the new `HPOSP`/`SIZEP` is already live on the tail rows of whatever is above (the 1-scanline slice of the hazard above - observed as a single 4x-wide line at a sprite's feet, spanning the platform's width); later and the band's first scanline still shows the old values. Park the commit after the `WSYNC` that ends the first half of that scanline, then use one more `WSYNC` to enter the band on cycle 0. Do not split the commit across the two halves of that scanline "to save cycles" - widths landing one scanline before positions is enough to redraw the feet line.
