---
name: atari8bit-pokey
description: >-
  Atari 8-bit POKEY — register map, timer/DLI audio, SIO serial protocol,
  polynomial counters, stereo POKEY, 4-bit digital sample playback (VCOUNT-sync).
---

# 05 — POKEY — Sound & I/O Chip

> **Key items:** AUDF1-4, AUDC1-4, AUDCTL $D208, STIMER $D209, RANDOM/SKREST $D20A, POTGO $D20B, IRQEN/IRQST $D20E, SKCTL/SKSTAT $D20F
> **Scope:** POKEY ($D200-$D20F, mirrored through page $D2): timers, sound, SIO serial, polynomial counters, stereo POKEY, 4-bit digital samples

---

## Quick-lookup

| Need | See § |
|---|---|
| Register map ($D200–$D20F) | §5.1 |
| Clock paths, `+1/+4/+7` divisors | §5.2 |
| Linked 16-bit channels | §5.2 |
| AUDC distortion / volume-only mode | §5.3 |
| SIO byte-level registers | §5.4 |
| RMT / TMC2 coexistence rules | §5.5 |
| Stereo POKEY address map | §5.6 |
| Polynomial counter roles | §5.7 |
| ALLPOT / RANDOM / IRQ / SKCTL / SKSTAT | §5.8 |
| 4-bit digital sample playback | §5.9 |

---

## §5.1  Register Map ($D200–$D20F)

Only low 4 address bits are decoded, so the canonical registers at
`$D200-$D20F` mirror through page `$D2`.

| Address | Read | Write |
|---|---|---|
| `$D200` | `POT0` | `AUDF1` |
| `$D201` | `POT1` | `AUDC1` |
| `$D202` | `POT2` | `AUDF2` |
| `$D203` | `POT3` | `AUDC2` |
| `$D204` | `POT4` | `AUDF3` |
| `$D205` | `POT5` | `AUDC3` |
| `$D206` | `POT6` | `AUDF4` |
| `$D207` | `POT7` | `AUDC4` |
| `$D208` | `ALLPOT` | `AUDCTL` |
| `$D209` | `KBCODE` | `STIMER` |
| `$D20A` | `RANDOM` | `SKREST` |
| `$D20B` | — | `POTGO` |
| `$D20C` | — | — |
| `$D20D` | `SERIN` | `SEROUT` |
| `$D20E` | `IRQST` | `IRQEN` |
| `$D20F` | `SKSTAT` | `SKCTL` |

---

## §5.2  Clock Paths & Timer Periods

```
AUDCTL bits:
  bit 7 = 1 -> use 9-bit polynomial, 0 -> 17-bit polynomial
  bit 6 = channel 1 clock = 1.79 MHz instead of 64/15 kHz
  bit 5 = channel 3 clock = 1.79 MHz instead of 64/15 kHz
  bit 4 = join channels 1+2 into one 16-bit divider
  bit 3 = join channels 3+4 into one 16-bit divider
  bit 2 = high-pass filter channel 1 with channel 3
  bit 1 = high-pass filter channel 2 with channel 4
  bit 0 = 1 -> 15 kHz base, 0 -> 64 kHz base
```

For pure-tone distortions (`$A0/$E0`) and most tuning work:

| Clock source | Frequency formula | Notes |
|---|---|---|
| 64 kHz base | `f = f_base / (2 × (AUDF + 1))` | `f_base = CPU / 28` |
| 15 kHz base | `f = f_base / (2 × (AUDF + 1))` | `f_base = CPU / 114` |
| 1.79 MHz on CH1/CH3 | `f = f_cpu / (2 × (AUDF + 4))` | AUDCTL bit 6 or 5 |
| Joined 16-bit at 1.79 MHz | `f = f_cpu / (2 × (AUDF_hi×256 + AUDF_lo + 7))` | CH1+2 or CH3+4 |

**Joined channels:** when AUDCTL bit 4 or 3 is set, the lower-numbered channel
supplies the low byte (`AUDF1` or `AUDF3`) and the higher-numbered channel
supplies the high byte (`AUDF2` or `AUDF4`). The audible control/output channel
is the higher-numbered one (`AUDC2` or `AUDC4`).

---

## §5.3  Distortion / Waveform Selection (AUDCx bits 4–7)

`AUDC` low nibble is volume (`0..15`). With bit 4 clear, bits 7:5 select the
polynomial path:

| Bits 7:5 | High nibble | Source |
|---|---|---|
| `000` | `$00` | 5-bit gating 17/9-bit polynomial |
| `001` | `$20` | 5-bit polynomial only |
| `010` | `$40` | 5-bit gating 4-bit polynomial |
| `011` | `$60` | 5-bit polynomial only (alternate tap pattern) |
| `100` | `$80` | 17-bit or 9-bit polynomial only |
| `101` | `$A0` | Pure tone |
| `110` | `$C0` | 4-bit polynomial only |
| `111` | `$E0` | Pure tone |

`AUDC` bit 4 = 1 forces **volume-only output**: the divider, distortion
selection, and high-pass filter are bypassed and bits 3:0 drive the 4-bit DAC.

---

## §5.4  SIO Serial Port

`SEROUT` is the transmit holding register; `SERIN` is the receive holding
register. POKEY shifts serial bytes as **1 start bit + 8 data bits + 1 stop
bit**. `SKREST` clears the latched serial/keyboard error bits in `SKSTAT`.

SIO protocol bytes such as ACK/NACK/COMPLETE/ERROR are **protocol-level values
on top of** these raw serial registers; they are not separate hardware states in
POKEY itself.

---

## §5.5  POKEY Timers → RMT / TMC2 Trackers

RMT and TMC2 are separate music-player ecosystems. Treat the player routine as
the ABI: call the documented init/play/stop entry points for that player build,
preserve any vectors you hook, and assume the player owns `AUDCTL`, `STIMER`,
and whichever POKEY channels it updates.

---

## §5.6  Stereo POKEY

The common stereo upgrade maps the second POKEY at `$D210-$D21F`. Use the same
low-nibble register layout as the primary chip:

| Primary | Stereo POKEY | Meaning |
|---|---|---|
| `$D200/$D201` | `$D210/$D211` | AUDF1/AUDC1 |
| `$D202/$D203` | `$D212/$D213` | AUDF2/AUDC2 |
| `$D204/$D205` | `$D214/$D215` | AUDF3/AUDC3 |
| `$D206/$D207` | `$D216/$D217` | AUDF4/AUDC4 |
| `$D208` | `$D218` | AUDCTL |
| `$D209` | `$D219` | STIMER |
| `$D20E/$D20F` | `$D21E/$D21F` | IRQEN/SKCTL |

Detection is upgrade-specific. Keep probes non-destructive, restore `IRQEN`,
`SKCTL`, and any timer state you disturb, and do not assume `$D210-$D21F`
exists on stock mono hardware.

---

## §5.7  Polynomial Counters

| Generator | Width | Practical role |
|---|---|---|
| Poly-4 | 4-bit | Short repeating noise / percussive textures |
| Poly-5 | 5-bit | Gates several distortion modes |
| Poly-9 | 9-bit | Optional shorter long-period noise (`AUDCTL` bit 7) |
| Poly-17 | 17-bit | Default long-period noise and `RANDOM` source |

---

## §5.8  ALLPOT / RANDOM / IRQ / SKCTL / SKSTAT

`ALLPOT` bits start at `1` after `POTGO` and clear to `0` as each paddle
reading completes. `RANDOM` returns 8 bits of the currently selected long
polynomial (17-bit by default, 9-bit when `AUDCTL` bit 7 is set).

| `IRQEN` / `IRQST` bit | Source |
|---|---|
| 7 | BREAK key |
| 6 | Keyboard data ready |
| 5 | Serial input ready |
| 4 | Serial output data needed |
| 3 | Serial transmit complete |
| 2 | Timer 4 |
| 1 | Timer 2 |
| 0 | Timer 1 |

`IRQEN` bits enable sources when set. `IRQST` is **active low**: a cleared bit
means the source is pending.

`SKCTL` layout:

| Bit | Meaning |
|---|---|
| 7 | Force serial BREAK |
| 6:4 | Serial clocking / mode select |
| 3 | Two-tone serial (cassette) mode |
| 2 | Fast paddle scan |
| 1 | Keyboard scan enable |
| 0 | Keyboard debounce enable |

`SKSTAT` layout:

| Bit | Meaning |
|---|---|
| 7 | Serial frame error latch |
| 6 | Serial input overrun latch |
| 5 | Keyboard overrun latch |
| 4 | Serial data ready |
| 3 | Shift key state |
| 2 | Last key still pressed |
| 1 | Serial input busy |
| 0 | Unused / undefined |

OS-friendly reset sequence:

```asm
        lda #$00
        sta SKCTL               ; stop/reset keyboard+serial logic
        lda #$03
        sta SKCTL               ; restore normal OS keyboard scan + debounce
```

---

## §5.9  4-Bit Digital Sample Playback

With `AUDC` bit 4 set, rapidly rewriting the low-nibble volume produces 4-bit
digital audio. `VCOUNT` changes every two scan lines, so one write per `VCOUNT`
step gives about **7.85 kHz on NTSC** and **7.78 kHz on PAL**. If you pack two
4-bit samples per byte, that corresponds to about **3.9 kB/s** of source data.

Use `audio/digital-audio.md` for a focused playback kernel and packing pattern.
