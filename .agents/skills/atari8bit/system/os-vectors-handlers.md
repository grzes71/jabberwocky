---
name: atari8bit-os-vectors-handlers
description: >-
  Atari XL/XE OS vectors, interrupt handlers, CIO/SIO entry points, IOCB
  lifecycle, device-handler hooks, and safe vector ownership rules.
---

# OS Vectors and Handlers

> **When to load:** The task touches VBI/DLI/CIO/SIO vectors, DOS entry points, device handlers, or OS coexistence.
> **Do not use for:** Bare register timing; load `hardware/antic.md`, `hardware/pokey.md`, or `hardware/cpu.md`.
> **Source note:** This file is self-contained; use the internal hardware references named above for register timing.

## Quick Lookup

| Need | See |
|---|---|
| DLI/VBI ownership | §1 |
| Deferred VBI install/return | §1.1 |
| OS entry vectors | §2 |
| CIO/IOCB lifecycle | §3 |
| SIO/DCB calls | §4 |
| Device handlers | §5 |
| Safe hook rules | §6 |

## 1. Interrupt Vectors

| Address | Name | Purpose |
|---|---|---|
| `$0200/$0201` | `VDSLST` | Display List Interrupt vector |
| `$0222/$0223` | `VVBLKI` | Immediate VBI vector |
| `$0224/$0225` | `VVBLKD` | Deferred VBI vector |
| `$D40E` | `NMIEN` | NMI enable: bit 7 DLI, bit 6 VBI |
| `$D40F` | `NMIST/NMIRES` | Read NMI status / write to clear latched NMI flags |

Rules:

- Set `VDSLST` before enabling `NMIEN` bit 7.
- DLI code entered through `VDSLST` normally saves what it uses and returns with `RTI`.
- Install VBI code with `SETVBV`; return deferred VBI code through `XITVBV`.
- Do not use `VDSLST` as a VBI vector.
- If multiple systems need DLI ownership, chain by changing `VDSLST` inside each DLI band or centralize ownership in one raster manager.

### 1.1 Deferred VBI via SETVBV / XITVBV

Install deferred VBI handlers through `SETVBV` and leave them through `XITVBV`. A raw `RTI` from a deferred VBI skips the OS VBI epilogue.

```asm
init_deferred_vbi
        ldx   #>my_vbi        ; X = high byte, Y = low byte
        ldy   #<my_vbi
        lda   #$07            ; deferred VBI slot
        jsr   SETVBV
        rts

my_vbi
        ; frame work here
        jmp   XITVBV          ; not RTI
```

Use immediate VBI only for short hardware-critical work. Put ordinary frame updates, input snapshots, music ticks, and buffer swaps in deferred VBI unless the program owns the whole NMI path.

## 2. OS Entry Points and User Vectors

| Entry | Address | Use |
|---|---|---|
| `DSKINV` | `$E453` | Resident disk handler: fills `DDEVIC`/`DTIMLO`/`DSTATS`/`DBYT`, then calls `SIOV` |
| `CIOV` | `$E456` | OS ROM entry for CIO command dispatch |
| `SIOV` | `$E459` | OS ROM entry for Serial I/O via the DCB |
| `SETVBV` | `$E45C` | Install immediate or deferred VBI vector |
| `SYSVBV` | `$E45F` | Enter OS immediate-VBI processing |
| `XITVBV` | `$E462` | Exit through the OS VBI path |
| `DOSVEC` | `$000A/$000B` | DOS command processor entry vector |
| `DOSINI` | `$000C/$000D` | DOS initialization vector |
| `RUNAD` | `$02E0/$02E1` | Binary-load run address |
| `INITAD` | `$02E2/$02E3` | Binary-load init address |
| `HATABS` | `$031A` | Device handler table |

Use symbolic labels from the assembler include file when available. Remember that `CIOV`/`SIOV` are callable ROM entry points, while `VDSLST`/`VVBLKI`/`VVBLKD` are RAM vectors the OS consults.

## 3. CIO and IOCB Lifecycle

IOCBs start at `$0340`, eight slots, 16 bytes each. `X` holds the IOCB offset (`$00`, `$10`, ... `$70`).

| Offset | Field | Meaning |
|---|---|---|
| `+0` | `ICHID` | Handler index; `$FF` means free IOCB |
| `+1` | `ICDNO` | Device / unit number |
| `+2` | `ICCOM` | CIO command byte |
| `+3` | `ICSTA` | Status byte |
| `+4/+5` | `ICBAL/ICBAH` | Buffer or filename address |
| `+6/+7` | `ICPTL/ICPTH` | Handler put/get routine pointer |
| `+8/+9` | `ICBLL/ICBLH` | Buffer length |
| `+10` | `ICAX1` | Auxiliary 1 |
| `+11` | `ICAX2` | Auxiliary 2 |
| `+12..+15` | `ICAX3..ICAX6` | Handler-specific auxiliaries |

Common CIO command bytes: `OPEN=$03`, `GET RECORD=$05`, `GET CHARS=$07`, `PUT RECORD=$09`, `PUT CHARS=$0B`, `CLOSE=$0C`, `STATUS=$0D`, `SPECIAL=$0E`.

Lifecycle:

1. Find a free IOCB (`ICHID = $FF`).
2. Fill `ICCOM`, pointer, length, and any `ICAXn` fields needed by the command.
3. Call `CIOV` with `X = IOCB offset`.
4. Check the returned status / N flag before consuming data.
5. Close the channel when finished.

## 4. SIO and DCB

SIO is below CIO. Use it for sector-level or custom-device work.

Important DCB fields:

| Field | Use |
|---|---|
| `DDEVIC` | Device ID |
| `DUNIT` | Unit number |
| `DCOMND` | Command byte |
| `DSTATS` | Direction / transfer mode |
| `DBUFLO/DBUFHI` | Data buffer |
| `DTIMLO` | Timeout |
| `DBYTLO/DBYTHI` | Byte count |
| `DAUX1/DAUX2` | Command-specific parameters |

Reverse rule: direct sector loaders usually call `SIOV`, not `CIOV`. Watch DCB writes before `SIOV` to recover the true protocol.

## 5. Device Handlers

`HATABS ($031A)` is the device handler table. Each entry is three bytes: device letter, handler-address low byte, handler-address high byte.

A handler table entry points to a jump table that provides the standard CIO operations (`OPEN`, `CLOSE`, `GET`, `PUT`, `STATUS`, `SPECIAL`, plus `INIT`).

Agent guidance:

- If code patches `HATABS`, treat it as OS integration, not ordinary vector use.
- If code opens `D:` through CIO, file semantics are DOS-dependent.
- If code calls `SIOV`, the program is likely bypassing DOS and using sectors or custom device commands.

## 6. Safe Hook Rules

- Save and restore previous vectors unless the program owns the whole machine.
- Disable NMI while changing `VDSLST`, display lists, or DLI chains.
- Do not call OS ROM routines while OS ROM is banked out; re-enable ROM first.
- Preserve registers according to the vector path: DLI handlers save what they use; deferred VBI exits through `XITVBV`.
- Separate shadow registers from hardware registers. VBI may update shadows; DLI must write hardware registers for immediate raster effects.
