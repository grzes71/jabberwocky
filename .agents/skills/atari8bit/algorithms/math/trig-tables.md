# Trig Tables

## 10.6 8-bit Sine/Cosine Tables

For animation and rotation, use one 256-byte signed sine table or one 128-byte
positive half-wave table plus quadrant folding. MADS can generate the table at
assembly time:

```asm
        .align $100
sine    dta b(sin(0,255,256,0,127))   ; 128 bytes, values 0..255, one half wave
cosine  equ sine+64                    ; 90-degree phase offset
```

That argument set emits **128** bytes, not 256, and the peak value is 255: it is
one 180-degree half wave, not a signed `0..127` table. `sine+64` is the
90-degree offset because the table covers 180 degrees in 128 steps. Check the
emitted size in the listing whenever the arguments change; the quadrant folding
below assumes a 256-byte signed table (values `$00..$7F` and `$80..$FF`).

If negative values are needed, fold by quadrant: `0..63` positive rising,
`64..127` positive falling, `128..191` negative falling, `192..255` negative
rising. Keep tables page-aligned for `LDA table,X`.

---
