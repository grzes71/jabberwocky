# Zero Page Stack

## 2.4  Zero-Page Idioms

| Idiom | Example | Notes |
|---|---|---|
| Increment 16-bit pointer | `INC ptr` / `BNE skip` / `INC ptr+1` | Increment high byte **only** when low byte wraps |
| Decrement 16-bit pointer | `LDA ptr` / `BNE skip` / `DEC ptr+1` / `skip DEC ptr` | Borrow propagates from low byte |
| Bit flag set/clear | `ORA #$80` / `AND #$7F` | Use explicit masks; assembler-specific `~` syntax is not portable |
| Backward loop | `LDY #n-1` / `...` / `DEY` / `BPL loop` | Standard 0..n-1 reverse walk |
| Fast ISR save | `PHA / TXA / PHA / TYA / PHA` | Stack save is the normal DLI/VBI pattern |

---

## 2.5  Stack & Subroutine Parameters

6502 stack: 256 bytes at `$0100-$01FF`, manipulated with `PHA/PLA`, `PHP/PLP`, `TSX`, and `TXS`.

Rules:

- `JSR` pushes the return address minus one; any inline-parameter trick must adjust that address and put a valid return address back before `RTS`.
- A bare `PLA/PLA` pair that consumes the return address is **not** a complete inline-parameter routine; if you do that, you must also provide an alternate way back to the caller.
- If you need self-relative data, a stack-relative `TSX`/indexed read pattern is often safer than destroying the return address.

---
