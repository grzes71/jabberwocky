# Data Banks Reloc

## 13.7 Data Types (.STRUCT/.ENDS, .ENUM/.ENDE)

```asm
; Structure definition
.struct point
    x   .byte
    y   .byte
.ends

; Instantiate — COUNT is the maximum element index, so [n] reserves n+1 elements
player     dta   point [0]    ; 1 struct (point = 2 bytes here)
enemies    dta   point [7]    ; 8 structs
other      point              ; shorthand for `dta point`, one struct

; Enumeration
.enum color_set
    black = 0
    red   = 2
    green = 4
    blue  = 6
.ende

    lda   #color_set(red | green)    ; == #color_set.red | color_set.green
```

### .ARRAY

```
.array  scr   .byte
    1,4,6                    ; [0..2]
    [12] = 9,3              ; [12..13]
.enda
```

---

## 13.8 Memory Banks — Virtual vs Hardware

### Virtual bank mode (`OPT B-`, default)

The MADS bank counter is a label-scope tool, not hardware: labels tagged with counter `0` are global,
labels tagged `>0` are local, and `=label` reads the counter while a leading `:` bypasses scope.
`.RELOC` blocks increment the counter automatically (`$0001..$FFF7`) and cannot be changed by hand.

### Hardware 16 KB bank mode (`OPT B+`) — Atari 130XE / banked cartridges

```asm
opt    b+                    ; bank-sensitive mode
        lmb #1               ; load bank counter (also calls @BANK_ADD -> new ORG)
        nmb                  ; bank counter +1
        rmb                  ; bank counter = 0, back outside the window
        lmb #5 , $6500       ; bank 5, next assembly address $6500 (OPT B+)
```

- `OPT B+` requires the macros `@BANK_ADD` (`MACROS\@BANK_ADD.MAC`) and `@BANK_JMP`
  (`MACROS\@BANK_JMP.MAC`) plus the labels `@TAB_MEM_BANKS` (table of PORTB values,
  e.g. filled by `PROCEDURES\@MEM_DETECT.ASM`) and `@PROC_ADD_BANK` (address of the
  bank-switch helper, which must live outside `$4000-$7FFF`).
- `LMB`/`NMB`/`RMB` change the MADS bank counter, force the `@BANK_ADD` macro (which emits
  the bank switch through `@PROC_ADD_BANK`) and set a new assembly address — default `$4000`
  for `LMB`/`NMB`, `$8000` for `RMB`.
- `=label` reads the bank counter of a label; a leading `:` bypasses bank scope
  (`lda :label5`, `@bank_jmp :bank2`). With counter `0` code must be outside `$4000-$7FFF`
  and labels are global; with counter `>0` code must be inside the window and labels are local.
- Runtime PORTB discipline is still yours: save/restore `PORTB` if DOS, SDX, BASIC or the OS
  ROM must survive, and keep NMI/VBI code and its return path outside the banked window.

Practical 130XE layout, from the MADS example `xms_banks.asm`:

```asm
        opt b+

@TAB_MEM_BANKS = $0400       ; table filled by @mem_detect
@PROC_ADD_BANK = $0600       ; helper outside the bank window

        org $2000
detect  jsr @mem_detect
        beq no_ext_ram

* bank #1 in the $4000-$7FFF window
        lmb #1
        .pages $40           ; assert a 64-page (16 KB) budget
bnk1    mva #"1" $bc40
        @bank_jmp :bnk2
        .endpg

* bank #2
        lmb #2
        .pages $40
bnk2    mva #"2" $bc40
        @bank_jmp :bnk1
        .endpg

* resident RAM, outside $4000-$7FFF
        rmb
        icl 'macros/@bank_jmp.mac'
        icl 'macros/@bank_add.mac'
```

---

## 13.9 Relocatable Code (MADS Format + SDX)

### MADS `.RELOC` / SDX relocatable output

```asm
        .reloc [.byte|.word]     ; start a relocatable block (bank counter auto-increments)
        .public main             ; exported symbol (aliases .global, .globl)
        .extrn  imported .word   ; external symbol (.ext type)
        .link   'module.obx'     ; link a previously assembled DOS/reloc file
```

- `.RELOC` emits a DOS-style header extended by 10 bytes; labels defined before the block must use
  `EQU`, and new labels inside the block must be indented (or MADS reads them as instructions).
- Relocatable references must be stored as data (`LDA _something` + `_something dta a(target)`),
  because a `lda <label` page-byte trick cannot be relocated.
- Blocks are merged with the `BLK UPDATE ...` pseudo-commands: `BLK UPDATE ADDRESS`,
  `BLK UPDATE SYMBOLS`, `BLK UPDATE EXTERNAL` (MADS extension, `$FFEE` header) and
  `BLK UPDATE NEW addr 'SYM'`. Public symbols get their own `BLK UPDATE PUBLIC` block —
  the `$FFFB` block is the *SDX-symbol* variant, not the public-symbol one.

Host-link pattern (from `tetris_reloc.asm` + `tetris_reloc_example.asm`):

```asm
; library/module source
        .reloc
        .public main
main    jsr init
        rts

; host program
        org $3127
        .link 'tetris_reloc.obx'
        run main
```

Export only the entry points the host needs and keep hardware registers as constants, not relocatable symbols.

### SpartaDOS X block types (MADS SDX documentation)

```asm
        blk  sparta  $2000   ; fixed-address SDX block, code at $2000
        blk  reloc   main    ; relocatable block in MAIN memory (EXTENDED = banked)
```

`BLK` is a pseudo-command, so it must be indented — in column 1 MADS reads `blk` as a label. Its forms are
`BLK N[one] addr`, `BLK D[os] addr`, `BLK S[parta] addr`, `BLK R[eloc] M[ain]|E[xtended]`,
`BLK E[mpty] n M|E`, `BLK U[pdate] S[ymbols|E[xternal]|A[ddress]|N[ew]`.

```
$FFFF  first block header (DOS compatible): start, end
$FFFA  fixed-address block header — identical to $FFFF, only marks the file as SDX
$FFFE  relocatable block: blk_num, blk_id (bit7 = reserve, no data), blk_off, blk_len
$FFFD  update block: blk_num, blk_len; payload = offsets plus $fc (end), $fd,a(ADDR),
       $fe,b(blk_num) and $ff (+$fa) commands
$FFFB  update block addressed by an SDX symbol name (8 ATASCII chars)
$FFFC  symbol definition block: blk_num, smb_off, SMB_NAME
```

`$FFFB`, `$FFFC` and `$FFFD` are consumed at load time and are not kept in memory.

---
