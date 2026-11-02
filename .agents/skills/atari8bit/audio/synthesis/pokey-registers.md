# Pokey Registers

## POKEY Overview

POKEY (POtentiometer and KEYboard) is the Atari 8-bit sound chip — four semiautonomous channels, each a frequency divider driving a polynomial counter. The divider value in AUDF determines pitch, the AUDC register configures volume and waveform distortion, and AUDCTL provides global channel configuration.

Each channel is independent: AUDF sets the divider (pitch), AUDC sets volume and the waveform/distortion source, and the global AUDCTL register reconfigures clock sources, 16-bit channel pairing, and high-pass filters. The same channels also provide the four timer interrupts and the serial clock used by SIO.

The four audio channels are named AUDF1/AUDC1 through AUDF4/AUDC4 in hardware. All POKEY audio registers live in the I/O page `$D200–$D20F`. A stereo upgrade adds a second POKEY, usually mapped at `$D210–$D21F`; no stock Atari 8-bit model (400/800/XL/XE) has one, and detection is upgrade-specific.

---

## Register Map

### Frequency Divider — AUDF1–4 ($D200, $D202, $D204, $D206)

Each AUDF register holds an 8-bit divide-by-N value. POKEY internally increments N by 1, so the effective divider is `AUDF + 1`.

```
f_out = f_clock / (2 × (AUDF + 1))
```

NTSC base clock is 63.921 kHz (often rounded to 64 kHz; use the precise value for musical tuning). PAL base clock is 63.337 kHz.

The 8-bit divider is coarse: one step of AUDF is about 7 cents near the bottom of the range (AUDF = `$FF`, ≈ 124 Hz) and the error grows with pitch, so use the 16-bit paired mode when accurate tuning matters. A440 in 8-bit mode is AUDF ≈ `$48` (≈ 438 Hz).

### Control Register — AUDC1–4 ($D201, $D203, $D205, $D207)

Bits 0–3 hold volume (0–15). Bit 4 selects forced-DC output — the PCM path. Bits 5–7 pick the distortion/noise polynomial.

```
+--+--+--+--+--+--+--+--+
| 7| 6| 5| 4| 3| 2| 1| 0|    AUDC
+--+--+--+--+--+--+--+--+
  \_______/  |  \______/
    poly      |   volume
    mode      |   (0-15)
              |
              forced output
              (bit4 = 1)
```

**Normal mode (bit 4 = 0):** distortion bits select the polynomial waveform. Distortion 5 and 7 skip the polynomial counter entirely — pure square wave, no noise floor. These are the modes used for musical lead lines and bass.

| Bits 5–7 | Polynomial | Sound character | Common use |
|----------|-----------|-----------------|------------|
| 000 | 5-bit + 17-bit | Complex noise | Explosion, wind |
| 001 | 5-bit only | Buzzy tone | Engine drone |
| 010 | 5-bit + 4-bit | Medium noise | Static |
| 011 | 5-bit only | Buzzy tone (variant) | — |
| 100 | 17-bit only | White noise | Hi-hat, snare |
| 101 | **None** | **Pure square wave** | Music lead/bass |
| 110 | 4-bit only | Rough percussive | Kick drum |
| 111 | **None** | **Pure square wave** | Music harmony |

Pure-tone control values range `$A0–$AF` (distortion 5) or `$E0–$EF` (distortion 7) with volume bits ORed in.

Bit 4 = 1 selects forced-DC output: the polynomial counter and frequency divider are both bypassed and the 4-bit volume value drives the DAC directly. This is the 4-bit PCM path (about 24 dB of SNR); a second channel can add a dithered LSB — see `filters-distortions.md`.

### Global Control Register — AUDCTL ($D208)

| Bit | Hex | Function |
|-----|-----|----------|
| 7 | $80 | 9-bit polynomial count (default 17-bit). Only heard on noise modes; pure-tone modes ignore this bit. |
| 6 | $40 | Channel 1 runs from the CPU clock instead of the 63.921 kHz base. Used for 16-bit high-precision and PDM sub-sample rates. |
| 5 | $20 | Channel 3 runs from the CPU clock (1.789 77 MHz). Join with bit 3 for 16-bit CH3+CH4 timing. |
| 4 | $10 | Join channels 1+2; CH1 becomes LSB, CH2 MSB. Single 16-bit divider: 65 536 steps. |
| 3 | $08 | Join channels 3+4; CH3 LSB, CH4 MSB. Independent of the CH1+CH2 pair. |
| 2 | $04 | High-pass filter: CH1 output sampled during CH3 divider ticks, gated through XOR. |
| 1 | $02 | High-pass filter: CH2 output sampled during CH4 divider ticks. |
| 0 | $01 | Switch the base clock from 63.921 kHz to 15.700 kHz (two octaves lower); useful for sub-bass drones. |

Bits 5 and 6 affect different channels — documentation frequently transposes them. Bit 5 = channel 3 tick source; bit 6 = channel 1 tick source.

Common AUDCTL presets:

```
$00   4-channel standard, 63.921 kHz base, 17-bit polynomial
$01   15.7 kHz base (bass)
$50   CH1+CH2 joined, CH1 at 1.789 77 MHz
$28   CH3+CH4 joined, CH3 at 1.789 77 MHz
$78   both pairs joined, both at 1.789 77 MHz
$60   CH1 + CH3 at 1.789 77 MHz (dual-channel PDM / filter tricks)
```

`SIOV` / disk / cassette / RS-232 activity overwrites `AUDCTL` with `$28` and silences
every voice, and the OS never restores the previous value. Re-assert presets such as
`$50`, `$78` or `$60` (plus `AUDC3`/`AUDC4`) after any serial-bus operation — see
`hardware/pokey.md` §5.2.1.

---

## Timer and Synch Registers

### STIMER ($D209)

Writing any value to STIMER resets all four divider counters simultaneously. Channels 1 and 2 are forced HIGH; channels 3 and 4 are forced LOW. The write is self-synchronizing — it is the only method to reset all dividers from a single write, and it is the starting point for tight PWM/PDM loops that require all channels aligned from a known state.

### IRQEN / IRQST ($D20E)

Timer interrupts fire when the channel divider reaches zero. `IRQEN` selects active IRQ sources; `IRQST` is read-only status at the same address. Clear a pending source by clearing that source's `IRQEN` bit, then set it again if the interrupt should remain enabled.

| Bit | Source | Event |
|-----|--------|-------|
| 0 | Timer 1 | AUDF1 divider reached zero |
| 1 | Timer 2 | AUDF2 divider reached zero |
| 2 | Timer 4 | AUDF4 divider reached zero |
| 3 | Serial output | Transmission of a byte finished |
| 4 | Serial output | Output data register needs a new byte |
| 5 | Serial input | A byte has been received (SERIN full) |
| 6 | Keyboard | A key was pressed |
| 7 | Break | BREAK key pressed |

Timer 1 and timer 4 are the usual choices for sample playback or a music tick; a timer interrupt is generated whenever the channel's divider underflows, so the ISR rate follows AUDF (plus the clock-path offset).

### SKCTL ($D20F) — POKEY Audio Initialization

```asm
LDA #$03   ; bits 0+1: enable keyboard scan and debounce
STA SKCTL  ; restore the OS keyboard-scan state
```

SKCTL bit 4 enables serial output and bit 5 selects the 1.79 MHz serial clock; the OS sets `SKCTL = $03` at cold start and switches modes during SIO/cassette I/O. Audio itself does not need SKCTL, but restore `$03` after any SIO or cassette operation that reconfigured POKEY.

---
