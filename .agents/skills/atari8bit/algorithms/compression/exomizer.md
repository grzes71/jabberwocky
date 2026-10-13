# Exomizer

## 12.3 Exomizer — Bit-stream LZ77 with offset tables

Exomizer is **not** an adaptive/statistical model like Upkr; it is LZ77 with a
compact bit-stream protocol plus a table of recently used offsets. Facts below
come from the exomizer 2.0/3.0 documentation and the decrunchers shipped in the
MADS `examples/compression/exomizer` directory.

Decrunch direction and memory:

- `mem`, `level` and `sfx` all crunch the file **backwards**. The standard 6502
  decruncher (`exodecrunch.asm`) is therefore a backwards "push" decruncher;
  forward decrunching needs a contributed decruncher such as Krill's
  `krilldecr.s`.
- The decruncher reads the crunched stream through a `get_crunched_byte`
  subroutine that must preserve X/Y and the carry flag. That indirection is what
  lets the same loop read from memory or from a forward-only stream.
- In-place decrunching is allowed: choose a destination that does not overwrite
  data still to be decrunched. There is no separate window or dictionary.
- Decrunchers do not touch the zero page.

Size and speed knobs:

- Decrunch tables are 156 bytes by default; `-P16` adds a dedicated offset table
  for length-3 sequences and grows them to 204 bytes.
- The sfx decruncher's size/speed trade-off is controlled by the `i_perf` symbol
  (`-1` shortest/slowest .. `2` largest/fastest, default `0`).
- `-M256` (limit sequence length to 256) makes the decruncher faster.

Bit-stream profile — the packer flags must match the decruncher build:

- `-P<n>`: bit 0 bit order (0 = little endian, 1 = big endian); bit 1 how runs
  longer than 7 bits are shifted; bit 2 implicit first literal byte; bit 3 align
  the bit stream to the start without the shift flag bit; bit 4 two or three
  length tables. `-P0` produces exomizer 2.0-compatible files, and `mem`/`level`
  modes default to `-P7`.
- `-T<n>` traits shorten/faster the decruncher by disallowing literal sequences
  (bit 0), length-1 sequences (bit 1) or long sequences (bit 2); `raw` mode
  defaults to `-T0`, `mem`/`level` to `-T4`.
- `-m<offset>` limits the maximum sequence offset, which the packer's
  circular-buffer decrunchers need.
- A literal-escape mechanism handles the occasional incompressible spot.

Practical rule for Atari loaders: pick one `-P`/`-T` profile, ship the matching
decruncher variant, and state both in the asset contract. A decruncher built for
the default profile will misdecode a `-P0` (exomizer 2.0) stream.

---
