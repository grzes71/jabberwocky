# Rle

## 12.1 RLE — Run-Length Encoding

Tebe/MadTeam format (Konop/Magnus/Probe/Seban/Tebe):

- The stream is a sequence of flag bytes; a flag of `$00` ends the stream.
- Flag LSB = `1` → **literal** run: `(flag >> 1) + 1` raw bytes follow.
- Flag LSB = `0` → **repeat** run: one byte follows, stored `(flag >> 1) + 1` times.
- Both run kinds therefore use the same count formula, `(flag >> 1) + 1`.

The matching packer (`rle.pas`) emits a repeat run only for runs of three or
more bytes, with flag `(run_len - 1) << 1`, and packs literals in runs of up to
128 bytes with flag `((len - 1) << 1) | 1`.

**RLE depacker (verified: 38 random/structured streams round-trip exactly):**

```asm
        ; ZP: in_ptr/in_ptr1 = input pointer, out_ptr/out_ptr1 = output pointer
        ;     cnt = remaining repetitions
rle_unp ldy   #0
@flag   jsr   getb
        beq   @done
        lsr                    ; C = run kind, A = count - 1
        sta   cnt
        bcc   @rep
@lit    jsr   getb
        jsr   putb
        dec   cnt
        bpl   @lit
        jmp   @flag
@rep    jsr   getb
@rpl    jsr   putb
        dec   cnt
        bpl   @rpl
        jmp   @flag
@done   rts

getb    lda   (in_ptr),y
        pha                    ; keep the byte and its N/Z through the bump
        inc   in_ptr
        bne   @gb
        inc   in_ptr1
@gb     pla
        rts

putb    sta   (out_ptr),y
        inc   out_ptr
        bne   @pb
        inc   out_ptr1
@pb     rts
```

`INC` clobbers N/Z, so `getb` pushes the byte and pulls it back after the
pointer bump to keep the caller's `BEQ @done` valid — the classic MADS depacker
instead does the pointer arithmetic *before* the final `LDA`.

### 12.1.2 Encoder cross-check

The packer emits one control byte followed by either a literal sequence or one
repeated byte, and terminates the stream with a zero byte.

```text
while data remains:
    if run_len >= 3:
        emit (run_len - 1) << 1        ; LSB=0: repeat
        emit repeated_byte
    else:
        emit ((literal_len - 1) << 1) | 1   ; LSB=1: literal, 1..128 bytes
        emit the literal bytes
emit 0                                 ; end of stream
```

Reading the control byte as `flag >> 1 + 1` for both kinds is what makes the
decoder loop identical for literals and repeats; an off-by-one here (`run_len -
2`) silently corrupts every repeat run.

---
