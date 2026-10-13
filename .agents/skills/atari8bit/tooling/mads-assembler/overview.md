# Overview

## Quick-lookup

| Need | See § |
|---|---|
| Overview and feature summary | §13.1 |
| Syntax / expression operators / addressing modes | §13.2 |
| .IF/.ELSE/.ENDIF + .REPT/.ENDR + .ALIGN | §13.3 |
| Label scope, temporary/self-modifying labels, `.DEFINE` | §13.4 |
| .MACRO/.ENDM (named params, `:0` count, `@+`/`@-` labels) | §13.5 |
| .PROC/.ENDP (@CALL/@PUSH/@PULL/@EXIT, typed params) | §13.6 |
| .STRUCT/.ENDS, .ENUM/.ENDE, .ARRAY | §13.7 |
| Memory banks — virtual (`OPT B-`) vs hardware (`OPT B+`) | §13.8 |
| .RELOC, BLK UPDATE, .PUBLIC/.EXT/.LINK | §13.9 |
| SDX block types ($FFFF/$FFFA/$FFFE/$FFFD/$FFFB/$FFFC) | §13.9 |
| 65816 addenda STZ/SEP/REP/BRL/JSL/MVN + .A8/.A16/.I8/.I16 (or .LONGA/.LONGI) | §13.10 |
| Practical MADS examples worth mining | §13.11 |

## 13.1 Overview

MADS is a cross-assembler commonly used for Atari 8-bit projects, with syntax familiar to XASM/FA users. This corpus documents **MADS 2.1.6** (the version pinned by the project `Makefile`, `c:/Apps/Mad-Assembler-2.1.6`).

Key features relevant to Atari 8-bit work:
- `.MACRO`, `.PROC` with typed parameters, software stack via `@CALL/@PUSH/@PULL/@EXIT`
- `.STRUCT` / `.ENUM` / `.ARRAY` type system
- Virtual banks (`OPT B-`) + hardware 16 KB bank mode (`OPT B+` with `LMB`/`NMB`/`RMB`)
- Relocatable MADS output (`.RELOC`, BLK update blocks) and SpartaDOS X files (`BLK SPARTA/RELOC`)
- `.GET [index] 'file'` loads a binary into a MADS one-dimensional array (`.PUT`/`.SAV` write it back;
  byte access is `.get[n]`), as used by the TMC/MPT relocator macros; `.LEN`/`.SIZEOF` report an
  `.ENUM`/`.ARRAY`/`.STRUCT` size
- `OPT R` — macro command size optimisation (MVA/MVX/MVY/MWA/MWX/MWY)
- `-x`/`-vu` drop or verify unreferenced `.PROC` procedures; `-l`/`-t` emit `.LST`/`.LAB` files

---
