# Overview

## Purpose

This file covers the memory map and system architecture for the Atari 8-bit in four progressive layers:
1. **Quick-lookup table** — scan or search for the fact you need; jump to the § directly
2. **Reference tables & register maps** — the dense lookup layer most frequently referenced
3. **Working code examples** — verified ASM/pattern snippets
4. **Deep reference notes** — edge cases, caveats, implementation rules

| Out of scope | See instead |
|---|---|
| DMA contention and cycle-stealing budget | §03-antic (ANTIC DMA section) |
| SIO DCB structure and frame format | §07-disk-file (SIO section) |

**Tip:** browse the Quick-lookup table below first; the § labels are clickable in most markdown viewers.

Only low address bits are decoded across much of the hardware page. In particular, the PIA mirrors through `$D300-$D3FF`, and writes to addresses currently mapped to ROM are ignored.

## Quick-lookup

| Need | See § |
|---|---|
| 64 K memory map | §2.1 |
| Zero-page and OS variable examples | §2.1 |
| PIA 6520 register table | §2.1 |
| PORTB OS/BASIC/self-test and 130XE banking bits | §2.3 |
| 130XE / larger XL/XE expansion caveats | §2.3 |
| Zero-page idioms | §2.4 |
| Stack and inline-parameter rules | §2.5 |

---
