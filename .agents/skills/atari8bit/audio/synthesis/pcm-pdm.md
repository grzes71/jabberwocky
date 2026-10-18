# PCM / PDM

## AUDC Forced-DC Output — PCM Entry Point

When AUDC bit 4 = 1:

- The polynomial counter output is disconnected.
- AUDF is ignored.
- The 4-bit volume value from bits 0–3 drives the DAC directly.
- No waveform period — the output is a static level, held until the next AUDC write.

This is how 4-bit PCM samples stream continuously on POKEY: each `ORA #$10 / STA AUDC1` pair replaces the current output level, so one write per scan line gives ≈15.7 kHz on NTSC and one write per VCOUNT step gives ≈7.85 kHz. Disable screen DMA (and keep the loop cycle-constant) so the writes stay evenly spaced.

Refer to `digital-audio.md` for full PCM timing methods and sample rate calculations.

---
