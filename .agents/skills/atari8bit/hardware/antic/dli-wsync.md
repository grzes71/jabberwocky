# Dli Wsync

## 3.6  DLI — Full Reference

The NMI path is `NMI vector $FFFA/$FFFB → OS NMI dispatcher → VDSLST`
(`$0200/$0201`) for a DLI, or the VBI vectors for vertical blank.

```
NMIEN ($D40E): $40 = VBI enable, $80 = DLI enable
VDSLST      : set this BEFORE enabling DLI
WSYNC ($D40A): write any value; CPU waits to the end of the current scan line
```

**DLI timing:** a DLI triggers on the **last scan line** of a DLI-tagged blank
or mode-line instruction. If you want clean changes at the next scan line,
write `WSYNC` first and then the hardware registers.

### Required DLI Boilerplate

```asm
        ; Install DLI — do this BEFORE enabling NMIEN
        lda #<my_dli_handler
        sta VDSLST
        lda #>my_dli_handler
        sta VDSLST+1

        lda #$C0            ; VBI + DLI enabled
        sta NMIEN

my_dli_handler
        pha                 ; save accumulator
        txa
        pha                 ; save X
        tya
        pha                 ; save Y

        ; --- critical register writes go here ---
        sta WSYNC           ; align to the next scan line
        lda #$0C
        sta COLPF0          ; $D016 — GTIA hardware register
        lda #$62
        sta COLPF1          ; $D017

        ; --- done, restore and return ---
        pla
        tay
        pla
        tax
        pla
        rti
```

### Hardware vs. shadow registers

Write **hardware** registers inside a DLI. Page-2 shadow registers are copied
back to hardware only during VBI.

| Shadow | Hardware |
|---|---|
| `GPRIOR` `$022E` | `PRIOR` `$D01B` |
| `PCOLR0` `$02C0` | `COLPM0` `$D012` |
| `PCOLR1` `$02C1` | `COLPM1` `$D013` |
| `PCOLR2` `$02C2` | `COLPM2` `$D014` |
| `PCOLR3` `$02C3` | `COLPM3` `$D015` |
| `COLOR0` `$02C4` | `COLPF0` `$D016` |
| `COLOR1` `$02C5` | `COLPF1` `$D017` |
| `COLOR2` `$02C6` | `COLPF2` `$D018` |
| `COLOR3` `$02C7` | `COLPF3` `$D019` |
| `COLOR4` `$02C8` | `COLBK` `$D01A` |
| `CHACT` `$02F3` | `CHACTL` `$D401` |
| `CHBAS` `$02F4` | `CHBASE` `$D409` |

### Simple chained DLI pattern

Use either a VBI to reset `VDSLST` each frame, or have each DLI point `VDSLST`
at the next routine.

```asm
dli1
        pha
        txa
        pha
        tya
        pha

        lda #<dli2
        sta VDSLST
        lda #>dli2
        sta VDSLST+1

        sta WSYNC
        lda #$34
        sta COLPF0

        pla
        tay
        pla
        tax
        pla
        rti

dli2
        pha
        txa
        pha
        tya
        pha

        lda #<dli1
        sta VDSLST
        lda #>dli1
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

## 3.7  WSYNC — Exact Timing

Writing to `WSYNC` halts the CPU until the end of the current scan line. The
next CPU access happens at the start of the following scan line.

Practical rules:

1. Put `WSYNC` **early** in the DLI if the visible register writes must land on
   the next scan line.
2. Do not assume one magic resume cycle for every video mode: DMA load and playfield
   width affect how much useful time remains afterward.
3. If a split is extremely cycle-sensitive, verify it on hardware or Altirra.

## 3.8  DLI Positioning — Multiple DLIs on Screen

- Put the DLI bit on the mode line or blank instruction whose **last scan line**
  should trigger the interrupt.
- Reset `VDSLST` from VBI if you want the chain to restart cleanly every frame.
- Use blank-line DLIs when you want setup time before a visible band begins.
