---
name: atari8bit-system
description: >-
  Atari 8-bit OS-ROM disable, ROM-aware interrupt coexistence, VCOUNT/WSYNC timing,
  RESET survival, BREAK-key polling, and DOS/SpartaDOS coexistence rules.
---

# 09 - System Hardening

> **Source note:** This file is self-contained.
> **Scope:** OS-ROM disable, ROM-aware interrupt design, VCOUNT, WSYNC, RESET survival, DOS coexistence
> **Key items:** PORTB $D301; NMIEN $D40E; NMIST $D40F; VCOUNT $D40B; WSYNC $D40A; SDLSTL $0230; BRKKEY $0011

## Quick-lookup

| Need | See § |
|---|---|
| OS-ROM disable / re-enable | §9.1 |
| Trampoline rule | §9.1 |
| VCOUNT / WSYNC timing | §9.2 |
| RESET survival 400/800 vs XL/XE | §9.3 |
| DOS / SpartaDOS coexistence | §9.4 |
| BREAK-key polling in long loops | §9.5 |

## 9.1 OS-ROM Disable & Trampoline Handler

### Disable OS ROM on XL/XE

`PORTB ($D301)` bit 0 controls whether the XL/XE OS ROM is visible:

- **Bit 0 = 1** — OS ROM visible at `$C000-$CFFF` and `$D800-$FFFF`
- **Bit 0 = 0** — underlying RAM visible instead

```asm
        lda PORTB
        pha
        and #$FE              ; clear bit 0 -> OS ROM off
        sta PORTB

        ; ... RAM-only code here ...

        pla
        sta PORTB             ; restore original banking
```

When OS ROM is off, hardware NMI/IRQ can still occur, but OS entry points such as `CIOV`, `SIOV`, `SETVBV`, and `XITVBV` are unavailable until ROM is visible again.

### Trampoline rule

If your code must coexist with VBI/DLI/IRQ while OS ROM is normally banked out, keep the rule simple:

1. Save the current `PORTB` state.
2. Re-enable OS ROM before tail-chaining into any OS routine.
3. Clear latched NMI status by writing to `NMIRES ($D40F)` when appropriate.
4. Restore `PORTB` before returning to your RAM-only code.

A bare handler that reads `NMIST` does **not** clear it; the latch is cleared by writing to `$D40F`.

## 9.2 VBI / VCOUNT Timing with OS-ROM Off

With OS services disabled, `VCOUNT ($D40B)` and `WSYNC ($D40A)` are the primary hardware timing tools.

- `VCOUNT` is ANTIC's vertical counter and advances every **two scan lines**.
- Typical maxima are about **130 on NTSC** and **155 on PAL** before wrap.
- `WSYNC` stalls the CPU until the next horizontal sync edge.

```asm
wait_vcount_80
        lda #$50
@poll   cmp VCOUNT
        bne @poll
        rts
```

Rules:

- On GTIA systems, prefer the `PAL` register at `$D014` for PAL/NTSC detection; use `VCOUNT` thresholds only as a fallback.
- Do not hard-code a single end-of-frame `VCOUNT` value for both standards.
- If you poll `VCOUNT`, use thresholds or wrap-aware logic instead of equality-only waits for frame-length detection.

## 9.3 RESET-Resistant Programs

| Machine | RESET behavior | RAM | Practical consequence |
|---|---|---|---|
| 400/800 | RESET key raises an NMI (ANTIC `NMIST` bit 5) and enters the OS warm-start path | Preserved | PIA state survives; reinstall vectors or display-list state as needed |
| XL/XE | RESET key generates hardware reset | Usually preserved on warm reset; undefined on power-on | Reinstall any custom vectors, display list, and banking state |

Practical rules:

- Use `WARMST ($08)` / `COLDST ($0244)` together with your own RAM signature if you need a warm-restart path.
- If your program owns `SDLSTL`, `VDSLST`, or VBI vectors, expect to reinstall them after RESET.
- 400/800-specific code must remember that the PIA is not reset by the RESET key.

## 9.4 DOS / SpartaDOS X Coexistence

DOS ownership on Atari systems is expressed through the standard loader and DOS vectors:

| Address | Name | Meaning |
|---|---|---|
| `$000A/$000B` | `DOSVEC` | DOS command processor entry |
| `$000C/$000D` | `DOSINI` | DOS initialization entry |
| `$02E0/$02E1` | `RUNAD` | Binary-load run address |
| `$02E2/$02E3` | `INITAD` | Binary-load init address |

Coexistence rules:

- Preserve or chain `DOSVEC`/`DOSINI` instead of replacing them blindly.
- Treat raw extended-RAM probing as unsafe once DOS or SpartaDOS X is active; SDX may already be using those banks for RAM disks or buffers.
- If you embed under DOS and still return to it, restore `SDLSTL`, BASIC/OS banking, and any handler-table changes before exit.

## 9.5 BREAK-Key Abort in Long Operations

The OS exposes BREAK-key state through `BRKKEY ($0011)`, not through a hardware IRQ-status register.

Practical rule:

- Long loops that bypass CIO can poll `BRKKEY` directly.
- When you detect BREAK, handle the abort and then restore `BRKKEY` to a nonzero idle value so later OS code does not see a stale BREAK.

```asm
BRKKEY = $11

check_break
        lda BRKKEY
        beq break_seen
        clc
        rts
break_seen
        lda #$80
        sta BRKKEY
        sec
        rts
```
