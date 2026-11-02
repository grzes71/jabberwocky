---
trigger: always_on
---

# Domain: 6502 Assembly (MADS)

## 1. Instruction Set & Limitations
- **Strictly MOS 6502:** Use ONLY official 6502 instructions. NO CMOS (PHX, PLY, BRA) or 65816 opcodes.
- **Processor Flags:** `INC` and `DEC` modify `Z` and `N`, but **NEVER `C` (Carry)**.
- **Arithmetic:** `ADC` and `SBC` must ALWAYS be preceded by an explicit `CLC` or `SEC`.
- **Syntax:** MADS only — `$` for hex, `%` for binary, `icl` includes, `org`, `dta`, `.proc`/`.endp`, `@local` and `?temp` labels.

## 2. Hardware & Memory Boundaries
- **Zero Page:** `$00`–`$7F` belong to the OS. Declare user variables ONLY in `zeropage.asm`, within `$80`–`$FF` (today `$80`–`$89` are used, `$8A`–`$FF` are free). Keep 16-bit pointers 2-byte aligned.
- **No Magic Numbers:** Never hardcode hardware addresses inside logic. Use the equates from `hardware.asm` (`WSYNC`, `PORTB`, `HSCROL`, `VDSLST`, `NMIEN`, `COLOR0`–`COLOR4`, `COLPF0`–`COLPF3`, `CHBASE`, `GPRIOR`, `STRIG0`, `RTCLOK`, `SETVBV`, …).
- **ROM banking:** OS ROM stays enabled (`PORTB` bit 0); BASIC ROM is disabled by `disable_basic` (`PORTB` bit 1). Never use `$C000`–`$DFFF` as RAM.
- **ANTIC 1 KB Rule:** A Display List must NEVER cross a 1 KB boundary without an explicit `JVB` or `LMS`, and `LMS` targets must keep the alignment used by the existing display lists.
- **Segment order:** top-level `org` blocks ascend (`$0800` → `$2800` → `$4000` → `$5C00` → `$6000` → `$6610` → `$6800` → `$6C00` → `$9000` → `$9A00` → `$B000`). The only sanctioned location-counter backtracking is the OS-vector stub pattern already present in `main.asm` (`org INITAD` … `org @end`, trailing `org RUNAD`). Never emit the same address range twice.
- **Runtime-reserved RAM (equates only — invisible to the memory checker):** PMG `$2000`–`$27FF`, HSCROL action ring buffer `$6000`–`$641F` (11 rows × 96 B), status bar `$6420`–`$646F`. Never place a new `org` segment there, even if `docs/memory_map.txt` reports the area as free.
- **Interrupts:** DLI/VBLANK handlers must save and restore every modified register (`PHA`/`PLA`, `TXA`/`PHA` … `PLA`/`TAX`), touch only hardware registers, and stay inside the scanline budget. Install DLI through `VDSLST`, deferred VBLANK through `SETVBV` type 7, and disable NMI via `NMIEN` when not needed.

## 3. Formatting
- **Cycle awareness:** time-critical routines (DLI/VBI handlers, HSCROL ring-buffer loops, VRAM column injection, flame collision gates) must document an explicit cycle budget in a block comment and explain any timing-driven decision. Per-instruction cycle counts with running totals only when auditing a contested path — do not clutter ordinary engine code.
- **Format:** `[Label]  [Mnemonic] [Operand]  ; [Comment + timing notes]`
- **Generated code:** everything under `gen/` is produced by Python tools — never hand-edit it; change the generator instead.
