# Deflate

## 12.4 DEFLATE — zlib-compatible Bitstream

DEFLATE on Atari 8-bit — figures from the zlib6502 `inflate` routine by Piotr
Fusik, shipped in the MADS `examples/compression/deflate` directory:

- The footprint is small enough to embed: `inflate` is **499 bytes** of code and
  constants, `inflate_data` is **764 bytes** of uninitialized data, and
  `inflate_zp` is **10 bytes** on page zero.
- **No 32 KB window buffer is required.** Matches are copied out of the output
  buffer itself, so only the compressed and the uncompressed data must fit in
  the 64 K address space.
- The compressed data is read sequentially and exactly once, so the two areas may
  overlap: uncompressed output may overwrite compressed bytes that have already
  been consumed.
- All three block types are decoded: stored (0), fixed Huffman (1) and dynamic
  Huffman (2); block type 3 is invalid and is not handled.
- Bits are consumed LSB-first. Huffman codes are accumulated into per-tree tables
  of `TREE_SIZE = 16` bytes; the alphabets are `LENGTH_SYMBOLS = 1+29+2 = 32`
  (literals, length codes, end-of-block), `DISTANCE_SYMBOLS = 30` and 62 control
  symbols in total.
- Length and distance codes carry extra bits (up to 5 for lengths, up to 13 for
  distances), fetched with the `GET_*_BITS` argument values.

Usage:

```asm
        mwa #compressedData inflate_zp
        mwa #uncompressedData inflate_zp+2
        jsr inflate
```

To read from a forward-only stream instead of memory, substitute the
`readByte`-based `getBit` shown in the upstream README.

Packing side: Zopfli produces the smallest DEFLATE streams; the same directory
ships `deflater`/`gzip2deflate` helpers that emit raw DEFLATE data from an input
file or a `.gz`.

---
