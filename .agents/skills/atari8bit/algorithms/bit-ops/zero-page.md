# Zero Page

## 11.6 Zero-Page Addressing (chapter02)

Every access to addresses `$0000`–`$00FF` uses the zero-page opcode variants,
which carry a **1-byte operand** instead of a 2-byte address. They are 1 byte
shorter than the absolute forms and usually 1 cycle faster (`LDA $80` is
2 bytes/3 cycles, `LDA $0200` is 3 bytes/4 cycles), and the indexed zero-page
forms never pay a page-cross penalty. That makes the zero page the natural home
for loop counters, pointers and temporaries.

Zero-page addressing modes:

```asm
        lda   $80              ; zero page
        lda   $80,x            ; zero page,X  — 1-byte operand
        ldx   $80,y            ; zero page,Y  — LDX/STX only
        lda   ($80),y          ; indirect indexed
        lda   ($80,x)          ; indexed indirect (also usable with JMP)
```

Which bytes are safe to use:

- `$00–$7F` holds OS variables (and BASIC/DOS work areas when they are resident).
- `$80–$FF` is the application area, but the OS floating-point package occupies
  `$D4–$EF` (`FR0 $D4`, `FRE $DA`, `FR1 $E0`, `FR2 $E6`, `FRX $EC`), so keep
  clear of that block if any OS FP call can run. See `system/memory-map.md` §2.1.
- This project's application ZP equates live in `zeropage.asm` (`$80–$FF`).
- The hardware stack is page 1 (`$0100–$01FF`), not the zero page.

Because the operand is a single byte, keep hot pointers and base addresses for
`,x`/`,y` table access inside `$00–$FF`. Zero-page indirect (`($80),y`) is also
the cheapest way to walk a buffer during a depack or copy loop.

---

---
