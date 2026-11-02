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
| `GPRIOR` `$026F` | `PRIOR` `$D01B` |
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
3. **Budget the phase, not the line.** `114` cycles is the *length of the scan line*,
   not your CPU time. ANTIC steals 9 (refresh) + 5 (PMG) + 1..3 (DL fetch) + 0..48
   (playfield) bytes out of it, and the handler only gets the remainder of its own
   trigger scanline. Keep a single DLI phase at **<= ~55 CPU cycles** while playfield
   + PMG DMA are active (see §3.9 and `dma-timing.md`).
4. If a split is extremely cycle-sensitive, verify it on hardware or Altirra.

## 3.8  DLI Positioning — Multiple DLIs on Screen

- Put the DLI bit on the mode line or blank instruction whose **last scan line**
  should trigger the interrupt.
- Reset `VDSLST` from VBI if you want the chain to restart cleanly every frame.
- Use blank-line DLIs when you want setup time before a visible band begins.

## 3.9  DLI Pre-triggering & WSYNC Counting in Multi-Scanline Modes

In multi-scanline modes (e.g. ANTIC Mode D = 2 scanlines/line, Mode 4/5 = 4 scanlines/line, Mode 2/3 = 8 scanlines/line), preparing hardware registers (such as PMG sizes, positions, priorities) before a time-critical scanline kernel often requires pre-triggering the DLI $N$ mode lines earlier.

### Scanline Accounting Rule

Because a DLI always triggers at cycle ~22 of the **last scanline** of the tagged display list instruction:
1. The CPU enters the DLI handler on that last scanline. The remainder of that line is
   ~85 **CPU slots** (114 - ~22 trigger offset - ~7 NMI entry) - these are *slots*,
   **not usable CPU cycles**: ANTIC keeps stealing bus cycles for refresh, PMG and
   playfield DMA, and the handler only gets what is left of its own trigger scanline.
2. Usable CPU cycles in that scanline = `114 - (9 refresh + 5 PMG + 1..3 DL fetch + 0..48 playfield)`, minus the ~29 slots spent before the handler starts.
3. The remaining scanlines before the start of the target mode line $2L$ equal:
   $$\text{Scanlines to wait} = 1 \text{ (remainder of trigger line)} + (N - 1) \times \text{ScanlinesPerModeLine}$$

#### Per-scanline CPU budget (DMA-aware)

| Scanline the phase runs on | Typical stolen bytes | Usable CPU cycles (PAL, 114/line) |
|---|---|---|
| Mode-line first scanline (playfield fetch, PMG on) | 9 + 5 + 40 + 3 = 57 | ~57 |
| Mode-line repeat scanline (no playfield re-fetch, PMG on) | 9 + 5 = 14 | ~100, ~70 after the DLI entry offset |
| Blank line with PMG DMA off | 9 + 3 = 12 | ~102 |

**Measured evidence** (Mode D 160x96, normal width, `SDMCTL = $3E`, PAL, 114 cycles/line):

| DLI phase | Length | Result |
|---|---|---|
| Setup phase on the pre-pas scanline | 55 cycles | aligned, no artifacts |
| Same phase grown to 79 cycles | 79 cycles | **kernel slipped one scanline** - every platform colour profile appeared one line late (stale enemy/secret colour on the first scanline, `sl0` + `sl1` black pair at the top) |
| Pas scanline colour/position commit | 48 -> 52 cycles | fits |

**Rule of thumb:** with playfield + PMG DMA active keep a single DLI phase at
**<= ~55 CPU cycles**, and never size a phase from the "~85 cycles" figure above.
If a phase needs more, split it onto a DMA-lighter scanline (blank line, repeat
scanline) or pre-trigger the DLI one mode line earlier ($N+1$ = one extra scanline
of setup room). Exact budgets depend on mode, width, scrolling and PMG settings -
verify cycle-sensitive splits on hardware or Altirra (see `dma-timing.md`).

### Mandatory `STA WSYNC` Sequence

To land cycle-accurately on cycle 0 of scanline 0 of target mode line $2L$:
- **Mode D (2 scanlines/line) with $N=1$ line pre-trigger:**
  - Remaining: 1 scanline (the trigger line's last scanline).
  - Requires **1x `STA WSYNC`**.
- **Mode D (2 scanlines/line) with $N=2$ lines pre-trigger (e.g., line $2L-2$):**
  - Remaining: 1 scanline (line $2L-2$, scanline 1) + 2 scanlines (line $2L-1$, scanlines 0 and 1) = **3 scanlines**.
  - Requires **3x `STA WSYNC`**:
    ```asm
    sta WSYNC   ; 1st: halts to end of trigger line (2L-2, scanline 1)
    sta WSYNC   ; 2nd: halts to end of pre-line (2L-1, scanline 0)
    sta WSYNC   ; 3rd: halts to end of pre-line (2L-1, scanline 1)
    ; CPU resumes at cycle 0 of scanline 2L (start of active band)!
    ```
- **Gotcha:** Using $N$ WSYNCs instead of calculating scanlines (e.g., 2 WSYNCs for $N=2$ mode lines) causes the kernel to start **1 scanline early** (on line $2L-1$ scanline 1) and exit **1 scanline early** (affecting the last scanline of the active zone).
- **Gotcha (phase overrun):** if the code before the first `STA WSYNC` exceeds the usable cycles of the trigger scanline, that `WSYNC` lands in the *next* scanline and every following `WSYNC` shifts with it - the whole kernel runs one scanline late. Symptom: per-scanline colour profiles appear shifted down by one line (the first scanline shows the previous zone's stale colour, `sl0` shows up on the second scanline).
- **Rule (late commit):** the *last* pre-band scanline is the only place from which an `HPOSP`/`SIZEP`/`SIZEM` commit becomes active exactly on the band's first scanline (see `../../gtia/player-missile.md`, "When a PMG Register Write Takes Effect"). Anything that must still show the *old* value on the scanlines just above the band has to be committed after those scanlines - i.e. in that last pre-line scanline, not on the trigger line.
- **Per-phase budgeting:** when one DLI does several unrelated jobs (band/row state, colour profiles, per-zone entities), split them across the `WSYNC`s and keep **each** phase under the DMA-aware budget. A phase may also be deliberately short, letting a `WSYNC` pad it, rather than packing in work that belongs to a later scanline - fewer cycles is not the goal, correct scanline ownership is.
