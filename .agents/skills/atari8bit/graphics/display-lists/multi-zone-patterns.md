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
