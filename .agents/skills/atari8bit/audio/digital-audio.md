---
name: atari8bit-digital-audio
description: >-
  Atari POKEY digital audio playback: 4-bit volume-only PCM/PDM, VCOUNT-timed
  sample kernels, nibble packing, channel selection, timing, and IRQ coexistence.
---

# 4-Bit Digital Sample Playback

POKEY volume is a 4-bit register ($0–$F for AUDCn volume bits). Rapidly writing volume-only values to AUDC3/AUDC4 produces 4-bit digital audio. Unpack a full 8-bit sample into two nibbles: upper nibble → high volume burst; lower nibble → next burst. At ~7.85 kHz (one nibble per VCOUNT step, i.e. every two scan lines on NTSC), the result is a clean 4-bit sample stream.

**Conversion pipeline:**

1. Convert PC audio to unsigned 8-bit mono RAW at the target rate (~7.8 kHz): `sox in.wav -t raw -r 7850 -u -b -c 1 out.raw`
2. Convert RAW to 4-bit packed: take the upper nibble of each byte, then pack two nibbles per byte, high nibble first.
3. In playback: read packed byte → output high nibble then low nibble → advance pointer once per byte.

**VCOUNT-synced sample-play kernel:**

```asm
; play_sample — 4-bit PCM on AUDC3, one nibble per VCOUNT step (~7.85 kHz NTSC)
; in:   sample_ptr/sample_ptr+1 -> packed sample data (2 nibbles per byte)
;       out_end/out_end+1       -> first byte past the sample data
; uses: Y (index), nibble_flag, last_vcount — reserve free zero-page bytes
; note: AUDC3 stays owned by this routine while it runs

sample_ptr   = $85          ; zero-page pointer pair: $85 = low byte, $86 = high
out_end      = $87          ; $87/$88
nibble_flag  = $84          ; 0 = high nibble next, 1 = low nibble next
last_vcount  = $89

play_sample
        lda #$00
        sta nibble_flag
        sta AUDC3           ; start silent
        ldy #$00
        lda VCOUNT
        sta last_vcount

?main_loop
?wait_tick
        lda VCOUNT          ; VCOUNT advances once per two scan lines
        cmp last_vcount
        beq ?wait_tick      ; one sample per VCOUNT step

        lda (sample_ptr),y  ; one packed byte = two 4-bit samples
        ldx nibble_flag
        bne ?low_nibble
        lsr                 ; high nibble of the packed byte
        lsr
        lsr
        lsr
        tax
        jmp ?store
?low_nibble
        and #$0F            ; low nibble
        tax
        iny                 ; only the low-nibble pass consumes a byte
        bne ?check_end
        inc sample_ptr+1
?check_end
        lda sample_ptr+1
        cmp out_end+1
        bne ?store
        cpy out_end
        bcs ?stop
?store
        txa
        ora #$10            ; bit 4 = volume-only output
        sta AUDC3           ; $D205
        lda nibble_flag
        eor #$01
        sta nibble_flag
        jmp ?main_loop

?stop
        lda #$00
        sta AUDC3           ; silence the channel
        rts
```

> [!WARNING]
> **Sample data size:** two 4-bit samples share one byte, so a full-rate 7.85 kHz stream costs ~3.9 KB per second (~24 KB for 6 seconds). For longer samples, page the data in from extended RAM or a bank-switched cart; when the source is outside the main 64K window, copy through a small ring buffer instead of pointing the sample pointer at banked memory. Keeping the sample inside consecutive pages avoids the pointer-high-byte update on every 256th byte.

> [!WARNING]
> **VCOUNT wrap:** VCOUNT (`$D40B`) is an 8-bit counter that increments every two scan lines and wraps after about 130 on NTSC and about 155 on PAL. Compare for equality against the previous value (as above) rather than assuming a universal maximum; when syncing to an absolute line, use the value for the target machine.

## Variable Pitch and Mixing

For one-shot effects, a fixed VCOUNT cadence is enough. For music engines or
sampled effects with pitch, keep playback time fixed and advance the sample
position by a fixed-point step.

```asm
; 16.8 fixed-point sample cursor. One output tick:
; samp_pos_hi:lo.frac points into sample data, step_hi:step_frac is pitch.
advance_sample
        lda   samp_frac
        clc
        adc   step_frac
        sta   samp_frac
        lda   samp_lo
        adc   step_lo       ; carry out of the fractional add propagates
        sta   samp_lo
        bcc   @same_page
        inc   samp_hi
@same_page
        rts
```

Use `step = 1.0` for native pitch, `2.0` for one octave up, `$0180` for 1.5x,
etc. This changes which source samples are consumed while the POKEY output rate
stays stable.

For multiple sample voices, mix into a wider accumulator before reducing to
POKEY's 4-bit volume:

- Convert nibbles to signed or centered values before summing.
- Use a volume lookup table: `scaled = sample * volume / 16` or `/64`.
- Clamp or bias the mixed result back to `0..15`, then OR with `$10` for
  volume-only mode.
- Keep the IRQ/VCOUNT output routine constant-time; do variable work in the
  main loop or a lower-priority VBI when possible.

Interpolation can improve high-pitch playback but costs cycles. On stock XL/XE,
prefer nearest-sample stepping unless the mixer has a very small voice count.
