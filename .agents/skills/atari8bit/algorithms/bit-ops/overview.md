# Overview

## Quick-lookup

| Need | See § |
|---|---|
| INC/DEC zero-page RMW + NMOS double write | §11.1 |
| INC/DEC $D40E NMIEN tricks | §11.1 |
| 9-bit rotate through carry (1 B/2 c) and 8-bit rotate left (3 B/4 c, CMP #$80 + ROL) | §11.2 |
| Garth Wilson nybble-swap — A-only (8 B, 12 c) | §11.2 |
| 9-bit rotate-left via PHP/ASL/ROL/PLP (14 c) | §11.2 |
| BIT trick — N=bit7, V=bit6, Z from A & operand | §11.3 |
| NMOS "BIT #imm" workaround (ZP power-of-two table) | §11.3 |
| Negative-index X descending loop (BPL) | §11.4 |
| Fast ISR/DLI register save/restore variants | §11.5 |
| Zero-page addressing (1-byte operand, 1 cycle faster) | §11.6 |
| Synthetic instructions and pseudo-ops | §11.7 |
| Lee Davison short idioms: carry toggle, range, true rotate, sign extend | §11.7 |
