# Filters Distortions

## High-Pass Filter Operation

High-pass mode is a fully digital gate inside POKEY, not an analog RC filter. The circuit is a D flip-flop fed by the paired channel divider, with its output XORed against the current filtered-channel state.

```
filtered-channel output
        |
        v
[D  flip-flop] <--- clock = paired-channel divider ticks
        |          (current vs. previous)
        v
[XOR] <-- current output
   |
   +---- output = current XNOR previous
```

Each tick of the paired divider captures the current filtered-channel level and holds it inside the D flip-flop. The XOR compares this stored value against the live output. If the two agree, XOR returns zero; if they differ, XOR returns one.

**Behavioural table:**

| Paired divider | Input frequency | Perceived effect |
|---------------|-----------------|-----------------|
| Slower than input | Input toggles several times per D tick | Tone passes essentially unchanged |
| Equal to input | Input and flip-flop toggle in lockstep | XOR stays 0 — the output nulls out |
| Faster than input | Input is held across many D ticks | Narrow pulses at the input rate: thinner, brighter tone |

The transition sits near the paired channel's frequency. POKEY's digital high-pass is
not a smooth analog roll-off — it is a series of peaks and nulls spaced at multiples of
the filter divider, which is why the effect is used as a "filter sweep" colour rather
than as a clean EQ.

**Filter in a PCM/PDM player:** gating one channel's output with another is how the classic
"filter" attack and percussion effects are built, and a common PCM trick is to run an LSB
channel in volume-only mode alongside the MSB channel so the two outputs sum to roughly one
extra bit of resolution. The exact divider ratios for such a player are implementation
specific — tune them by ear rather than deriving them from a formula.

---

### PCM Pre-Processing (Essential)

Before writing PCM samples to POKEY AUDC, a three-step conversion pipeline
is mandatory to avoid clipped transients, unintelligible speech, and
click/pop artefacts.  Skipping any of these steps will produce audible
quantisation floor, DC drift, or noise-floor hiss at sample-rates above 4 kHz.

| Step   | Action                               | Why                                     |
|--------|--------------------------------------|-----------------------------------------|
| **1 Normalize** | Scale input to full 0‑15 range       | Under‑used range wastes quantisation SNR |
| **2 DC Offset** | Centre values around 7‑8             | Silence emits ~$07, not $00/$0F — prevents speaker thump  |
| **3 Dither**    | Add low‑order random noise before    | Smooths quantisation banding in sibilants; converts structured |
|                 | quantisation                          | noise floor into benign random hiss     |

```asm
; Pre-process 8-bit sample in A → 4-bit volume value in A
pre_process:
    lsr                       ; keep the top nibble (4-bit output range 0-15)
    lsr
    lsr
    lsr
    clc
    adc dither_bit            ; 0 or 1, e.g. from a random-bit source, for dithering
    and #$0F                  ; stay inside 0-15
    ora #$10                  ; bit 4 = volume-only output
    rts
```

For dual-channel PDM: carry the DC-centred MSB through directly; the LSB
nibble receives only the dithered residue (no separate DC-offset pass).


---
