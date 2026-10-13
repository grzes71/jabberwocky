# Lz4

## 12.2 LZ4 — LZ4-family Decompression

Format overview (LZ4 block format, Yann Collet):
- LZ4 is an LZ77-type format: each sequence is a literal run followed by a match
  copy.
- A sequence starts with a one-byte token: the high nibble is the literal
  length, the low nibble is the match length **minus 4** (the minimum match is
  4 bytes, so a low nibble of 0 means 4).
- A nibble value of `$F` means extension bytes follow: each next byte is added to
  the length, repeating while it equals `$FF`. A nibble of exactly `$F` is
  followed by at least one extension byte, even if that byte is 0.
- The match offset is a 2-byte little-endian backward distance (1..65535; the
  value 0 is invalid/corrupt).
- The block ends right after the final literal-only sequence, which has no
  offset field. The last 5 bytes of a block are always literals, which is why
  blocks shorter than 12 bytes do not compress.

No separate window is needed on Atari: the output buffer *is* the history, so
the match source is just `output - offset`. The MADS example `unlz4.asm` needs
only two 16-bit pointers, a token byte and a 16-bit length; it patches absolute
operands instead of using `(zp),y`, so the depacker must live in writable RAM.

```asm
        mwa #packed inputPointer
        mwa #output outputPointer
        jsr unlz4

unlz4   jsr get_byte             ; token
        sta token
        :4 lsr                   ; A = literal length
        beq read_offset          ; zero literals is legal
        cmp #$0f
        jsr getLength            ; consumes the $0f extension bytes
        ; ... copy that many literals byte by byte ...
read_offset
        jsr get_byte             ; offset low byte
        ; ... offset high byte; source = outputPointer - offset ...
        ; match length = (token & $0f) + 4, again extended on $0f
```

`getLength` adds extension bytes while they equal `$FF`, and the terminating
byte must be less than `$FF`; use `INW` for the 16-bit pointer bumps. The exact
end-of-block handling in the example is its own convention for pre-trimmed
`koronis.lz4` data — a plain LZ4 block ends on the literal-only last sequence.

---
