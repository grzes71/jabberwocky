---
name: atari8bit-vbxe
description: >-
  VBXE — FPGA-based GTIA replacement for Atari 8-bit: FX/GTIA_emu register map, blitter, sprites, XDL, MEMAC windows, polygon/video examples.
---

# 15 — VBXE — Video Board XE (Exotic Hardware)

> **When to load:** The task requires VBXE detection, FX registers, XDL setup, VRAM access, blitter use, palette work, or VBXE example triage.
> **Scope:** VBXE: FX/GTIA_emu register map ($D6xx/$D7xx), MEMAC windows, blitter, sprites, XDL, polygon/video examples
> **Key items:** `$D6xx`/`$D7xx` register page; FX registers at page+`$40`–`$5F`; CORE_VERSION `$D640`/`$D740`; MINOR_REVISION `$D641`/`$D741`; MEMAC B control `$D65D`; blitter `$D650`–`$D654`
> **Primary sources:** Altirra's VBXE emulation — `github.com/ilmenit/AltirraSDL` (`src/Altirra/source/vbxe.cpp`, `src/Altirra/h/vbxe.h`, `src/ATHelpFile/source/vbxe.xml`). The VBXE FX 1.26 manual is the vendor reference for the FX core but no online copy could be located, so it is cited by title only — every register fact below is cross-checked against Altirra.

## Quick-lookup

| Need | See § |
|---|---|
| VBXE in one paragraph | §15.1 |
| FX core spec table (512KB VRAM, 21-bit palette) | §15.2 |
| Register layout table | §15.3 |
| FX CORE_VERSION `$D640` / MINOR_REVISION `$D641` | §15.4 |
| FX detection (KMK/DLT 2009, MEMAC B_CTL trick) | §15.4 |
| XDL and minimal init | §15.5 |
| VRAM / MEMAC / blitter | §15.6 |
| EN code-examples index | §15.7 |

## 15.1 What Is VBXE

VBXE (Video Board XE) is an FPGA-based internal add-on designed by T. Piorek that replaces the GTIA on Atari 8-bit XL/XE machines. The FPGA core can be upgraded in software; the corpus includes FX 1.26 documentation. Altirra emulates VBXE as an optional device.

VBXE operates in parallel with ANTIC and GTIA: it shadows ANTIC/GTIA writes for standard display compatibility while adding an extended display list (XDL), overlay planes, an attribute map, and a hardware blitter. GTIA collision behavior remains tied to the standard ANTIC/GTIA path.

**Core families:**

| CORE_VERSION | Core |
|---|---|
| `$10` | FX v1.xx (extended graphics + blitter + palette) |
| `$11` | GTIA emu v1.xx (GTIA-compatible only, no FX extras) |
| other | Reserved / unknown |

The register window must live in PBI space at either `$D6xx` (the usual configuration, and what most existing software assumes) or `$D7xx`. With Ultimate1MB also active, the window is configured through the U1MB setup rather than by the emulator/hardware jumper.

## 15.2 FX Core Specs

VBXE FX core v1.26 — hardware capabilities:

| Feature | Value |
|---|---|
| VRAM | 512 KB local; blitter/DMA run 8 memory cycles per ANTIC cycle (≈14.3 MHz) |
| Palette | 21-bit RGB (7 bits per channel) = 2 097 152 colours; 4 palette planes × 256 entries (1024 simultaneously) |
| Overlay modes | SR 320/336×256c; HR 640×16c; LR 160×256c; text 80-col |
| XDL | Independent display list; runs from VRAM without CPU rewrite per frame |
| Attribute map | Cells with programmable width/height and X/Y scroll, one colour set per cell |
| Blitter | Copy/fill at one memory cycle per byte written (source reads cost extra); IRQ on completion |
| Sprites | Software only — 1×1 – 256×256 G8-sized blits; 256 colours each; quantity limited by blitter throughput |
| Priority | Programmable per-layer (PM0–PM3, PF0–PF3, COLBAK, overlay) |
| RAMBO core | The `'r'` firmware variant emulates a RAMBO 256 KB memory expansion from VBXE's VRAM |

VBXE 1.0 introduced the board; VBXE 2.0 shrank the FPGA configuration time.

## 15.3 Register Layout

VBXE decodes one 256-byte register page, either `$D600` (slot 0, the usual configuration) or `$D700` (slot 1). The FX registers live at **page + `$40` … page + `$5F`** — i.e. `$D640-$D65F` or `$D740-$D75F`. Offsets below `$40` are not registers (reads return `$FF`); offsets from `$C0` up expose the FPGA config latch (D0 = DATA0, D1 = DCLK, D2 = /CONFIG, D7 = CONF_DONE).

| Reg (page-relative) | R/W | Description |
|---|---|---|
| `$40` | W | VIDEO_CONTROL — bit0 = XDL enable, bit1 = extended color, bit2 = overlay opaque, bit3 = 15-level transparency |
| `$41-$43` | W | XDL_ADR0/1/2 — 19-bit XDL address in VRAM |
| `$50-$52` | W | BL_ADR0/1/2 — 19-bit address of the blitter BCB list |
| `$55-$58` | W | P0-P3 — overlay priority |
| `$5D` | W | MEMAC_B_CONTROL — bank/access for the `$4000-$7FFF` window |
| `$5E` | W | MEMAC_CONTROL — page base, size and access for the MEMAC A window |
| `$5F` | W | MEMAC_BANK_SEL — MEMAC A bank |

### FX CORE registers ($D640–$D65F and $D740–$D75F)

| Reg | Write | Read |
|---|---|---|
| `$Dx40` | VIDEO_CONTROL | CORE_VERSION |
| `$Dx41` | XDL_ADR0 | MINOR_REVISION |
| `$Dx42` | XDL_ADR1 [15:8] | `$FF` |
| `$Dx43` | XDL_ADR2 [18:16] | `$FF` |
| `$Dx44` | CSEL (palette select 0–3) | `$FF` |
| `$Dx45` | PSEL (playfield palette) | `$FF` |
| `$Dx46` | CR red | `$FF` |
| `$Dx47` | CG green | `$FF` |
| `$Dx48` | CB blue | `$FF` |
| `$Dx49` | COLMASK entry mask | `$FF` |
| `$Dx4A` | COLCLR write-back | COLDETECT read-out |
| `$Dx4B–$Dx4F` | reserved | `$FF` |
| `$Dx50` | BL_ADR0 (BCB list address low) | BLT_COLLISION_CODE |
| `$Dx51` | BL_ADR1 (bits 8-15) | `$FF` |
| `$Dx52` | BL_ADR2 (bits 16-18) | `$FF` |
| `$Dx53` | BLITTER_START | BLITTER_BUSY |
| `$Dx54` | IRQ_CONTROL | IRQ_STATUS |
| `$Dx55–$Dx5C` | P0–P3 + reserved | `$FF` |
| `$Dx5D` | MEMAC_B_CONTROL | `$FF` |
| `$Dx5E` | MEMAC_CONTROL | MEMAC_CONTROL (read-back) |
| `$Dx5F` | MEMAC_BANK_SEL | MEMAC_BANK_SEL |

> x = 6 or 7 depending on which page VBXE is decoded at.

**GTIA emu core** (`CORE_VERSION = $11`): `$Dx40–$Dx48`, `$Dx4A` are write; rest read as `$FF`.

---

## 15.4 VBXE Detection

### FX core 1.20+ (KMK/DLT, 2009)

> **MADS/CPU-mode note:** this is plain 6502 source. For 65816 code add `opt c+`, and write accumulator addressing bare (`asl`, `lsr`, `rol`, `ror`) — MADS 2.1.7 rejects `ASL A`. The `get_fx_version` listing below already uses the bare `asl`/`ror`/`lsr` forms.

```asm
MEMAC_B_CTL = $5d
vbxe_detect
        lda   #$d6
        sta   _vbxe_write+2
        ldy   #MEMAC_B_CTL
        jsr   ?clr
        jsr   ?try
        bcc   ?ret
        inc   _vbxe_write+2
?try    ldx   $4000
        jsr   ?chk
        bcc   ?ret
        inx
        stx   $4000
        jsr   ?chk
        dec   $4000
?ret    rts
?chk    lda   #$80
        jsr   _vbxe_write
        cpx   $4000
        beq   ?clr
        clc
?clr    lda   #$00
_vbxe_write
        sta   $d600,y
        rts
```

Return: **C=0** → VBXE found; `_vbxe_write+2` = `$D600` or `$D700`.

### FX revision read

```asm
        ; run after vbxe_detect
        ; out: C=0 FX core confirmed, vb_rev = revision byte,
        ;      bit 7 of vb_rev set when the RAMBO 'r' firmware is present

get_fx_version
        lda   #$00
        sta   vb_rambo
        sta   vb_page
        lda   _vbxe_write+2
        sta   vb_page+1
        ldy   #$40
        lda   (vb_page),y    ; CORE_VERSION ($D640 or $D740) = $10 for FX
        cmp   #$10
        bne   not_fx
        iny
        lda   (vb_page),y    ; MINOR_REVISION
        cmp   #$ff
        beq   not_fx
        asl
        ror   vb_rambo       ; bit 7 = RAMBO/shared-memory flag
        lsr
        sta   vb_rev          ; revision byte, e.g. $26 = 1.26
        clc                   ; FX OK
        rts
not_fx  sec
        rts
```

Return: **C=0** → FX core confirmed; `vb_rev` = revision byte; bit 7 = RAMBO/shared-memory variant (`vb_rambo`).

**Revision byte structure** (bit 7 valid from FX 1.21):
- bit 7 = 1 → RAMBO ('r') firmware, i.e. VBXE's memory is reused as a 256 KB RAMBO expansion
- bits 6–0 → version digits: `$26` = 1.26, `$24` = 1.24, `$20` = 1.20 (Altirra supports exactly 1.20/1.24/1.26 and collapses other values to these)
- Compatible cores share the upper digit (FX 1.20 software runs on 1.24).

FX 1.20 predates the RAMBO bit, so a 1.20 core can never report bit 7.

---

## 15.5 XDL and Minimal Init

XDL is VBXE's extended display list. It controls overlay mode, palette selection, priority, scrolling, and attribute-map behavior independently from ANTIC's display list.

Minimal setup path:

1. Detect VBXE and record whether it decodes at `$D600` or `$D700`.
2. Disable or stabilize display changes while programming registers.
3. Upload palette entries through `CSEL/PSEL` and `CR/CG/CB`.
4. Place the XDL in CPU-visible memory or VRAM as required by the selected mode.
5. Write XDL address registers.
6. Enable XDL processing through `VIDEO_CONTROL` (`$D640` bit 0).

XDL design rules:

- Keep XDL state changes at stable scan-line boundaries.
- For interlace or field-dependent effects, use paired entries and avoid one-scan-line toggles unless the effect is intentionally unstable.
- Treat VBXE overlay priority separately from GTIA player/playfield priority.

## 15.6 VRAM, MEMAC, Palette, and Blitter

VBXE has 512 KB of local VRAM. The CPU accesses it through MEMAC windows and the blitter.

| Mechanism | Use |
|---|---|
| MEMAC A | CPU-visible banked VRAM window; base page, size (4/8/16/32 KB) and CPU/ANTIC access are set by MEMAC_CONTROL `$D65E` with the bank in MEMAC_BANK_SEL `$D65F` |
| MEMAC B | Fixed `$4000-$7FFF` (16 KB) window; bank plus CPU/ANTIC access set by MEMAC_B_CONTROL `$D65D`; also the window the standard detection routine probes |
| Palette registers | 21-bit RGB entries written through CSEL `$D644` / PSEL `$D645` / CR-CG-CB `$D646-$D648` (the 7-bit channel rides in bits 7..1) |
| Blitter list | Copy/fill/attribute operations executed by VBXE hardware; BCB list address in `$D650-$D652`, started via `$D653` |
| Blitter busy/IRQ | Poll BLITTER_BUSY (read `$D653`: bit1 = busy, bit0 = loading BCB) or use the blitter IRQ (`$D654`) before reusing blitter state |

Blitter workflow:

1. Build a blitter command/list in the expected format for the FX core.
2. Point blitter address registers at the command/list.
3. Start the blitter.
4. Poll `BLITTER_BUSY` or handle the blitter IRQ.
5. Do not overwrite source, destination, or command memory until complete.

Common hazards:

- FX core revisions before 1.20 differ in MEMAC B behavior.
- Register base can be `$D600` or `$D700`; never hard-code one after detection found the other.
- VRAM writes through a MEMAC window are bank/window-relative, not CPU-linear.
- Palette and XDL changes can tear if made mid-frame without a planned raster boundary.

## 15.7 EN Code Examples (Index)

### Candle Family

| File | Description |
|------|-------------|
| Candle/1200xl/a1200xl.asm | 1200XL logo replacement; RMT music; inflate; MEMAC A @0x3000; palette fade |
| Candle/scroll/scroll.asm | Sinus H/V scroll via XDL; cross-fade between VRAM pages |
| Candle/slideshow/slide.asm | 16-DAP image slideshow; blitter fades, palette switching |

### Electron Family

| File | Description |
|------|-------------|
| Electron/bt.asm | 80-col text H-scroll demo; blitter scroll, rnd foreground colour |
| Electron/cmap.asm | Attribute map gradient demo; MEMAC B + blitter |
| Electron/mtest1.asm | CPU→VRAM write/readback integrity test |
| Electron/mtest2.asm | Dual-bank VRAM write/readback test |
| Electron/vbmp.asm | 320×200 256-col BMP file browser via blitter DAP |
| Electron/vbxefx.asm | FX macros + palette for MADS |
| Electron/scroll/sk1.asm | Full scroller demo; sinus fonts over plasma |

### KMK / Fox / Rybags / Other

| File | Description |
|------|-------------|
| `KMK/textmode.s` | 80×24/80×32 text mode; cursor, Tab⇒colour, inverse video via blitter |
| `KMK/dactest.s` | DAC test; blitter fill, BCB chain, 4-palette setup |
| Fox/st2vbxe.asx | ST→VBXE converter demo; xex binary |
| `Rybags/Quadrillion/` | Full game port from Commodore Plus/4; VBXE v1.24+ required |
| `TeBe/plasma/` | Plasma effect; colour map 40×49, sinus tables, XDL raster |

---

Full production builds such as the LAMERS Group `oldschool` directory (10 FX parts) and `wb2` directory (8 FX parts plus bank-switcher) are useful for studying real VBXE asset streaming, XDL changes, and blitter-heavy effects.

Source notes: VBXE register, detection and MEMAC semantics above are cross-checked against Altirra's VBXE emulation (`github.com/ilmenit/AltirraSDL`, `src/Altirra/source/vbxe.cpp` + `src/ATHelpFile/source/vbxe.xml`) and the FX 1.26 vendor manual (cited by title; no online copy located).
