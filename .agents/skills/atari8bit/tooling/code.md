---
name: atari8bit-code-examples
description: >-
  Atari 8-bit code catalog — sieve, Tetris (1065-line GETRIS engine), RLE depacker, GTIA9++ boilerplate, 40x40 CHBASE, demoscene index.
---

# 14 — Code Examples & Demoscene Catalog

> **Scope:** Working code examples + Atari demoscene catalog: 128B, 256B, 1024B productions; graphics, sound, math, and data-format examples
> **Key items:** sieve, Tetris (1065-line GETRIS engine), RLE depacker, GTIA9++ boilerplate, 40x40 CHBASE, demoscene index
> **Scope:** Ready-to-read Atari 8-bit code patterns: small programs, RLE, display-list tricks, demoscene techniques, VBXE production patterns, and MADS idioms.

## Quick-lookup

| Need | See § |
|---|---|
| Sieve of Eratosthenes | §14.1 |
| Tetris engine (LUT-driven pieces + NMI HUD) | §14.1 |
| RLE encode/decode + Pascal Tebe encoder | §14.2 |
| GTIA mode 9++ display list + DLI VSCROL patch | §14.2 |
| 40x40 character-mode CHBASE (TMC v2.00) | §14.2 |
| 128B productions (BeatTheStars, greenmil, rand_walker, waveanim) | §14.3 |
| 256B productions (fire, sintro, water, galactic_bearing, quatari, deform, ...) | §14.3 |
| 1024B algorytm_v08i (Agenda/svoy, 4 FX sections) | §14.3 |
| Candle/Electron VBXE production file index | §14.4 |
| MADS example corpus map | §14.6 |
| MADS .STRUCT/.PROC/65816 snippet | §14.7 |

## 14.1 Math and Algorithm Examples

### Sieve of Eratosthenes (sieve.asm)

```asm
; C-port benchmark run 10 times; flags = 255 bytes at $8000
; .var i,prime,k,count,iter .word  - zero-page words via .VAR
; #while .word i <= #size ... #end - code-generation loops
; adw/inw macros index the flags table, wait() syncs on RTCLOK (lda:cmp:req 20)
; printf comes from .link 'libraries/stdio/lib/printf.obx'; run main
```

### Tetris (tetris.asm — GETRIS engine v1.1 by TeBe/Madteam, 1065 lines)

Playfield engine, `buf = $a000`, 32 × 128 cells:
- 9 tetrominoes (`klocek1`…`klocek9`) with up to 4 rotation states, addressed through the low/high byte
  LUTs `l_klocek`/`h_klocek` and `l_test`/`h_test` (each rotation has a `.test` label).
- Self-modifying `.macro sta_kloc` / `.macro lda_kloc` patch the draw/erase operands; `.proc put_klocek`,
  `.proc test_posX` and `.proc test_posY` place and test a piece.
- Display list: `dta $4f,a(buf)` (LMS + mode line) + `:height-1 dta $f` + `dta $41,a(ant)`.
- No DLI colour split — a custom NMI handler (vector written to `$FFFA/$FFFB`, enabled with NMIEN `$40`)
  switches the display-list pointer (`mwa #ant $d402`) and reads the stick with a delay-based latch
  (`read_joy`, `delay_joy`, `old_joy`).

---

## 14.2 Graphics Code Examples

### RLE Encode/Decode (compression/rle/rle.asm + pc/rle.pas)

RLE depacker credited to "Konop, Magnus, Probe, Seban, Tebe":
- `getByte` reads through `lda $ff00,x` / `inputPointer equ *-2`, i.e. the source pointer's
  low byte must be `$00`; `inx` + `sne` + `inc inputPointer+1` walks the stream.
- Control byte: `0` = end of stream, LSB set = literal run, LSB clear = repeat run;
  the following count byte is the run length minus one.

```pascal
// RLE_ENCODER V1.2 by Tebe/Madteam (Free Pascal: fpc -Mdelphi -O3 rle.pas)
procedure save_rle(const a, ile: byte);      // repeat run, flag LSB = 0
begin
  tmp[0]:=(ile-1) shl 1;  tmp[1]:=a;  blockwrite(f,tmp,2);
end;
// literal run: a:=(i shl 1) or 1; then i+1 bytes
// the encoder ends the file with a single 0 byte and rejects input > 64 KB
```

### GTIA Mode 9++ (mode 9++.asm)

Real display list (Jaskier's TMC 2.00 intro, `graphics/mode 9++/mode_9++.asm`):
```
dl  dta $90,$6f,a($f000)   ; DLI+HSCROL blank line, then LMS+VSCROL mode-F line at $f000
    :29 dta a($2f8f)       ; 29 x {8f,2f} = 58 mode-F lines, DLI on every line
    dta $41,a(dl)          ; JVB back to dl
```
`$22` is written to SDMCTL ($22F), `$40` to PRIOR ($26F, enabling GTIA modes), DLI vector $200 and
NMIEN `$C0`. The DLI only patches VSCROL: `sta $d40a` (WSYNC) then `lda #13 / sta $d405` followed by
`lda #3 / sta $d405` — those two VSCROL values are what turn one ANTIC mode-F line into a 9++ line pair
(this is not a COLPF colour patch).

### 40×40 Character Mode (40x40.asm)

Fonts at `$8000` (`font1`, loaded with `ins 'tmcprog.fnt'`) and `$8400` (`font2`, produced by
`fontcopy` at init, 6 bytes per character). The DLI alternates both the fine scroll and the
character base, so CHBASE gets the *high byte* of the font address ($80 / $84):

```asm
; VBI resets the working values each frame: mva >font2 fontwsk / mva #2 linewsk
dli      pha
         sta $d40a           ; WSYNC
         lda #0
linewsk  equ *-1             ; VSCROL, toggled 2 <-> 5 after every use
         sta $d405
         eor #7
         sta linewsk
         lda #0
fontwsk  equ *-1             ; CHBASE = $84 ($8400), toggled $84 <-> $80
         sta $d409
         eor #4
         sta fontwsk
         lda $d20a           ; RANDOM
         sta $d01a
         pla
         rti
```

Display list: `dta $a0,$e2,a(screen)` + `:19 dta $82,$a2` + `dta b($41),a(dlist)`, with the
"THETA MUSIC COMPOSER VER 2.00 BY JASKIER" screen text at `$5000`. The VBI (`$222`) resets the
working font/line values each frame; `wait_vbl` polls RTCLOK `$21c`.

### RLE depacker skeleton (`compression/rle/rle.asm`)

```asm
rle_depacker
        sta inputPointer+1

loop    jsr getByte          ; 0 = end of stream
        beq stop
        lsr @                ; LSB -> carry: 1 = literal run, 0 = repeat run
        tay                  ; count-1
lp0     jsr getByte          ; literal run: fetch a new byte each pass
lp1     sta $ffff
outputPointer equ *-2
        inw outputPointer
        dey
_bpl    bmi loop             ; Y underflowed -> next control byte
        bcs lp0
        bcc lp1              ; repeat run: re-store the same byte

getByte inx
        sne
        inc inputPointer+1
        lda $ff00,x          ; low byte of the source pointer must be $00
inputPointer equ *-2
stop    rts
```

The encoder is the PC-side tool, not an assembler routine: `compression/rle/pc/rle.pas`
(`rle input rle_file`, max 64 KB) emits `(flag, byte)` pairs and terminates with a single `0`.

---

## 14.3 Demoscene Catalog

### 128-Byte Productions (demoscene/128B/ (see §14.3 table))

| Production | Author | Year | Technique |
|------------|--------|------|-----------|
| **BeatTheStars** | Ivo van Poorten | 2018 | POKEY beat from envelope/frequency tables; star field = random stack bytes pulled with `txs`/`pla` into PMG0 (`$d000`); NMI disabled so the stack can be used |
| **greenmil** | goblinish | — | Writes COLBK (`$d01a`) after every `WSYNC` from a mirrored luma table; wide playfield via SDMCTL `$22f` |
| **rand_walker** | — | — | OS graphics call `$ef9c` selects mode 9 (16 shades), then OS locate `$f18f` / plot `$f1d8` random walk from RANDOM (`$d20a`) with a coordinate-mask table; colour shadow `$2fb` |
| **waveanim** | — | — | `waveanim.asx`: wave glyph built at assembly time, drawn through CIO put-byte (`$0b`) via `$e456`, setting ICBUFA/ICBUFL, CHBAS `$2f4`, LOGMAP `$2b2`, CRSINH `$2f0` |

### 256-Byte Productions (demoscene/256B/ (see §14.3 table))

**Main catalogue:**

| Production | Author | Year | Technique |
|------------|--------|------|-----------|
| **fire** | — | — | ANTIC mode 0 screen (`$9c40`) with a 16-step grey charset at `$4000` + PRIOR `$40`; 4-neighbour average written through self-modified absolute operands; screen cleared with OS put-char `$f1a4` |
| **galactic_bearing** | Ilmenit (Jakub Dębski), music stRing | — | `FRACTALS=3`, `VERTEXES=8` chaos-game fractal (`fractal_number`, `vertex_x/y`); needs OS Rev 2 |
| **sintro** | MadTeam | 1997 | `tcos` table built by quarter-mirroring (`mva`, `eor #$ff`), PMG0-3 positions `$d000-$d003` animated per line; `.zpvar` variables; signature `Sintro 256B MADTEAM '97` |
| **water** | SeBan/Slight | 2021 | `buf1`/`buf2` double buffer; 4-neighbour averaging then `lsr`; random value added to the second buffer's high byte |
| **quatari** | Ilmenit | 2020 | 4 FX in `.local` scopes (maze/sierpinski/lights/landscape) share one screen buffer |
| **porazka** | taquart | — | Plasma and "kefrenki" sections selected with `bit timer`; sine table built from `dta b(sin(32,19,128,0,31))` and mirrored with `eor #$3f` into four quadrants; per-line COLBK (`$d01a`) + HSCROL (`$d404`) patches |
| **deform** | pr0be/laresistance | 2004 | ANTIC buffers at `$2800`/`$2c00`, `texture.dat` + `tabu.dat`, texture generated per frame |
| **glenches** | pr0be | — | 3D wireframe using precomputed `xtab`, `ztab`, `bitmask`, `sqrtab` lookup tables |
| **LANDSCAPE** | tr1x/Agenda | 2021 | Terrain edges via `f=(f-1)*x`; stars are PMG0 (`hposp0`/`sizep0`/`grafp0`) driven by a `starpos` table; PRIOR pushes PMG behind the mountains |

**Kefrens interlaced bars (`kefrens/`)** — these three sources are **xasm** files (`.xsm`), not MADS:

| File | Technique |
|------|-----------|
| `kefrens_1st_twt.xsm` | Blank every 2nd line; sine start offsets pushed/popped LIFO with the stack (`pha` … `pla / adc #+1` / `pla / adc #-2`) |
| `kefrens_interlaced.xsm` | Dual sine LUT `$600`/`$680`; `+$11` added per pixel to the shade buffer; interlace by `eor #$03` on the display-list low byte (`$d402`) |
| `kefrens_final.xsm` | Solid lines; `make_dl`/`put_line` build the display list at `$bc20` (no DLI); `inc $d500,x` is the 7-cycle delay that replaces `sta $d40a` (`WSYNC`) |

### 1024-Byte Productions (demoscene/1024B/ (see §14.3 table))

**algorytm_v08i.asm (Agenda/svoy, Forever 2019, 766 lines)** — 4 FX sections:

| FX | Mechanism |
|----|-----------|
| fx1_vbl | Random GTIA/graphics-mode changes, central logo, background PMG bars |
| fx2_vbl | Full-screen text-mode pictures with charset swapping, interleaved with pseudorandom sound-synced sections |
| fx3_vbl | Randomized display list + title text over a rapidly cycling background colour, PMG logo blinking to the sound |
| fx4_vbl | Randomized charset changes as fast as possible |

Sections are dispatched through the `RUN_L`/`RUN_H` (frame work) and `EXIT_L` (prep) tables indexed by
a `SECTION` counter. The sound is hand-coded from the tables `kickbas`, `sndkick5`/`sndkick6`,
`seclead` and `leadnotes` — there is no RMT player in this file.

---

## 14.4 Candle/Electron VBXE Production Files

| File | FX / Technique |
|------|----------------|
| Candle/scroll/scroll.asm | Horizontal/vertical sinus scroll via XDL; cross-fade between VRAM pages |
| Electron/scroll/sk1.asm | Full scroller: sinus fonts over plasma background |

*Note: full VBXE production detail including Candle/1200xl (logo replacement, RMT, inflate, MEMAC A), slideshow, Candle/slideshow, and Electron/vbmp.asm is in the VBXE reference file in the Atari 8-bit skill collection.*

---

## 14.6 MADS Example Corpus Map

Use the bundled MADS example patterns in this skill collection when a task needs
runnable idioms rather than isolated algorithms.

| Area | Files to inspect | Useful pattern |
|---|---|---|
| Syntax and scoping | `if_else.asm`, `while.asm`, `rept.asm`, `local*.asm`, `macro_proc_local.asm`, `struct_enum.asm` | Compile-time control, local namespaces, macro-local labels, typed structures. |
| Loaders and file I/O | `Boot.asm`, `file_loader.asm`, `file_header.asm`, I/O and stdio library examples | Boot sectors, dual-address relocation, CIO-style library calls, command-line parsing. |
| Banking and detection | `xms_banks.asm`, `detect_memory.asm`, `detect_cpu.asm`, `detect_sdx.asm`, `stereo_detect.asm` | 130XE/RAMBO bank setup, CPU and SDX capability probes, stereo POKEY detection. |
| Raster graphics | MCP DLI/IRQ, mode 9++, 40x40 and lepix examples | DLI/IRQ colour splits, interlace modes, VSCROL/CHBASE timing. |
| Compression | RLE, LZ4, Exomizer, and NuCrunch examples | Depacker loop structure and workspace trade-offs. |
| Music players | Tracker relocator and ProTracker examples | Relocatable RMT/MPT/CMC/TMC players and module-data inclusion. |

Treat `.obx`, `.lst`, and `.lab` beside source files as verification artifacts: use listings and labels to confirm generated addresses, but summarize techniques from source in English.

---

## 14.5 Demo Skeleton Template

```asm
; Demo skeleton: init -> deferred VBI + DLI -> main loop
; Target machine type: Atari XL/XE, MADS assembler

        org    $2000            ; standard XEX load address

; ============================================================
; INIT
; ============================================================
init
        sei                    ; mask IRQs during init
        lda    #$00
        sta    NMIEN            ; disable DLI/VBI during setup

        ; set up display list
        lda    #<display_list
        sta    SDLSTL            ; OS shadow: $0230
        lda    #>display_list
        sta    SDLSTL+1

        ; set up deferred VBI through the OS
        ldy    #<my_vbi
        ldx    #>my_vbi
        lda    #$07              ; deferred VBI slot
        jsr    SETVBV

        ; set up DLI vector. VDSLST is DLI-only, not VBI.
        lda    #<my_dli
        sta    VDSLST
        lda    #>my_dli
        sta    VDSLST+1

        ; enable VBI + DLI
        lda    #$C0             ; $40=VBI, $80=DLI
        sta    NMIEN

        ; Zero page init
        ldx    #$00
@zloop  lda    #$00
        sta    zpage,x
        inx
        bne    @zloop

        cli                    ; re-enable IRQs
        ; fall through to main loop

; ============================================================
; MAIN LOOP
; ============================================================
main_loop
        ; per-frame work here (input -> update -> render -> VBI swap)
        jmp    main_loop

; ============================================================
; VBI
; ============================================================
my_vbi
        ; per-frame deferred work:
        ;   - update scroll accumulators
        ;   - swap display-list pointers
        ;   - clear VSCROL/HSCROL shadow state
        jmp    XITVBV            ; correct deferred VBI exit path

; ============================================================
; DLI
; ============================================================
my_dli
        pha
        txa
        pha
        tya
        pha
        sta    WSYNC             ; align visible register writes
        ; write hardware color/GTIA/ANTIC registers here, not shadows
        pla
        tay
        pla
        tax
        pla
        rti

; ============================================================
; Data
; ============================================================
display_list
        .byte  $70,$70,$70       ; 3 x 8 blank scanlines (top border)
        .byte  $41               ; JVB -> jump and wait for VBI
        .word  display_list
```

---

## 14.7 MADS `.STRUCT` / `.PROC` / 65816 Example

```asm
; MADS structures and procedures (checked against MADS 2.1.6)
; .STRUCT: field names are byte offsets; the struct label equals its total size
; .PROC with .REG/.VAR parameters, or the @CALL/@PUSH/@PULL/@EXIT software stack

        .struct Vert3d
x       .byte
y       .byte
z       .byte
        .ends

verts   dta Vert3d [2]           ; 3 records — [count] is the maximum index

; .REG: parameter names must be built from A/X/Y, at most 3 bytes
        .proc SetColors (.byte a,x) .reg
        sta $d016
        stx $d017
        rts
        .endp

        SetColors #$0e,#$42      ; parameters land in A and X, then JSR

; software stack (no .REG/.VAR): needs the @CALL/@PULL/@EXIT macros and the
; @PROC_VARS_ADR/@STACK_ADDRESS/@STACK_POINTER labels (defaults $0500/$0600/$FE)
        .proc SetDLPtr (.word addr)
        mwa   #display_list addr
        rts
        .endp

        SetDLPtr #display_list   ; '#value' = by value

        opt   c+                 ; 65816 code must be enabled
        .a8                      ; emits SEP #$20 (tracked A = 8 bit)
        lda   #$4c
        .a16                     ; emits REP #$20
        lda   #$1234
```
