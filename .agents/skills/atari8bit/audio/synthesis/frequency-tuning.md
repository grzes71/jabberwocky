# Frequency Tuning

## 16-Bit Mode

Joined-channel pairs construct a 16-bit divider from two 8-bit registers:

```
N = AUDF_LSB + (AUDF_MSB × 256)      ; AUDF1 (LSB) + AUDF2 (MSB), or AUDF3 + AUDF4
f_out = f_clock / (2 × (N + K))
```

`K` depends on the clock path selected in AUDCTL: 1 for the 64 kHz / 15 kHz base
clocks, 4 for a single channel clocked at 1.79 MHz (AUDCTL bit 6 or 5), and 7 for
a joined pair clocked at 1.79 MHz.

A440 from a 16-bit pair at the 1.789 77 MHz clock (K = 7):

```
N = 1 789 770 / (2 × 440) − 7 = 2 027 = $07EB
AUDF1 (CH1, LSB) = $EB
AUDF2 (CH2, MSB) = $07
```

When channels are joined, the **higher-numbered** channel owns the output: `AUDC2`
(or `AUDC4`) selects distortion and volume, and the lower channel contributes only
its divider value as the low byte — leave its `AUDC` at zero.

---

## Base Clock Reference Values

NTSC:

```
CPU clock         1.789 770 MHz
POKEY base        63.921 kHz   (CPU ÷ 28)
POKEY alt         15.700 kHz   (CPU ÷ 114)
```

PAL:

```
CPU clock         1.773 447 MHz
POKEY base        63.337 kHz
POKEY alt         15.560 kHz
```

For musical pitch it is the 1.789 77 MHz value that matters when paired with 16-bit mode. For typical 8-bit game tones the 63.921 kHz (NTSC) / 63.337 kHz (PAL) base clock is sufficient and AUDF values are portable.

---

## Dual Channel Precision Tuning

A single 8-bit divider quantises pitch: with `N = AUDF + 1` the step between
neighbouring values is `1200 × log2((N+1)/N)` cents — about 7 cents at the bottom
of the range and far worse for high notes. Running the pair as a 16-bit divider at
1.79 MHz shrinks that step by roughly a factor of 256 for the same note, which
keeps the error well below one cent across the musical range, so pre-computed
tables of both `AUDF` bytes are the normal approach.

Remember to set `AUDCTL` for the pair before writing the dividers (`$50` = CH1+CH2
joined at 1.79 MHz, `$28` = CH3+CH4), and remember that both bytes must be written
for a new pitch to take effect.

---

### PDM Best Practices — Cycle-Perfect Timing

PDM tolerates no unpredictable variation in code-path length.  Every entry/exit
path through the sample ISR must take exactly the same number of cycles regardless
of which branches are taken. One cycle of extra latency on a single sample shifts
the LSB slot phase, producing audible phase-ringing/ghosting.

```asm
; ----
; Cycle-counted PDM sample ISR path (NMOS 6502, no page crossing on LDA)
; ----
;   LDA (zp),Y          5 cycles  (load 8-bit sample)
;   4 × LSR             8 cycles  (MSB nibble)
;   ORA #$10            2 cycles  (forced volume-only output)
;   STA AUDC1           4 cycles  (output MSB)
;   AND #$0F            2 cycles  (extract LSB nibble)
;   ORA #$10            2 cycles  (LSB forced output)
;   STA AUDC2           4 cycles  (pulse LSB channel)
;   INY                 2 cycles
;   BNE taken           3 cycles  (2 when not taken — pad with one NOP)
;   RTI                 6 cycles
;   Total              38 cycles  — identical on every path
;---

; ─── Hardware state required before PDM ISR entry ───
;   STA DMACTL ($D400)  $00 — screen DMA steals cycles unpredictably
;   STA NMIEN  ($D40E)  $00 — no DLI/VBI can pre-empt the ISR
;   SEI                     — no POKEY timer IRQ may fire mid-pattern
; ────────────────────────────────────────────────────

; Each BCC/BCS/BNE/BEQ pair must perform exactly identical
; path extensions so that the branch-taken and branch-not-taken totals match.
```

Without all three hardware-lock steps (`STA DMACTL`; `STA NMIEN`; `SEI`) the ISR
path length is non-deterministic. A single stolen DMA cycle shifts the LSB slot
boundary by 1/Nth of a carrier period, producing a comb-filter notch or phase-skip
that is audible as a metallic ping.

---
