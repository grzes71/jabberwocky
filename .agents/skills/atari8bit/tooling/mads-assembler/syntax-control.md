# Syntax Control

## 13.2 Syntax and Operands

Numbers: `$1f` or `0x1f` hex, `%0101` binary, plain decimal. Character literals: `'A'` = ATASCII, `"A"` = INTERNAL code — only the first character is significant, and a trailing `*` inverts it (`dta c'abcd'*`). Typed/character data goes through `DTA C'...'`/`DTA D'...'`, `.BY`, `.SB`, `.CB`, `.BYTE`.

A two-character literal is a 16-bit word (`'AB'` = `$4142`), so it only fits word operators: `mwa #'XY' $80` is valid, `lda #'AB'` fails with *Value out of range*.

**Expression operators:** `+ - * / % & | ^ << >> = == <> != < > <= >= && ||`, unary `+ - ~ ! < > ^ = :`. The XASM-style words `MOD AND OR XOR SHL SHR NOT` are **not** MADS operators (they fail with *Extra characters on line* / *Undeclared label*).

Expressions use 64-bit signed arithmetic internally; results truncated to 32-bit unsigned for memory addresses.

**Addressing modes:**
```
lda #$01             ; immediate
lda $80              ; zero page
lda $0200            ; absolute
lda ($80,x)          ; indexed indirect (zp,X)
lda ($80),y          ; indirect indexed (zp),Y
lda $0200,x          ; absolute indexed X
lda $0200,y          ; absolute indexed Y
```

There is no `(abs),Y` mode on 6502/65816 — `lda ($0200),y` is rejected (*Illegal addressing mode*). Mnemonic suffixes force the operand size: `.b`/`.z` byte, `.w`/`.a`/`.q` word, `.l`/`.t` 24-bit (`lda.w $12` = `AD 12 00`).

---

## 13.3 Directives and Control Flow

| Directive | Purpose |
|-----------|---------|
| `ORG addr[,addr2]` | Assembly address; `addr2` = address written in the file header (dual-address load). `ORG [header,...],addr[,addr2]` replaces the DOS header, and the XASM form `ORG addr,*` assembles at `addr` without opening a new file block |
| `.A8 / .A16` | With `OPT C+`: emit `SEP #$20` / `REP #$20` and set the tracked 65816 accumulator width |
| `.I8 / .I16` | With `OPT C+`: emit `SEP #$10` / `REP #$10` and set the tracked 65816 index width |
| `.LONGA ON|OFF`, `.LONGI ON|OFF` | 65816 only: set the assembler's assumed M/X width **without** emitting `SEP`/`REP` |
| `.ALIGN N[,fill]` | Align the assembly address to an N-boundary (defaults `N=$0100`, `fill=0`) |
| `.NOWARN` | Suppress the warning for the current line |
| `.PRINT / .ECHO` | Compile-time text/number output |
| `.ERROR / ERT` | Compile-time error halt; accepts strings and expressions |
| `.DEFINE name expr` (`.DEF`) | Define a single-line macro; referencing `name` expands to `expr` |
| `.UNDEF name` | Disable a `.DEFINE`d single-line macro (otherwise *Undeclared macro*) |
| `.PAGES N / .ENDPG` | Require the enclosed code to fit in N pages (`Page error` otherwise); `.ENDPG` is mandatory |
| `.LEN label` / `.SIZEOF` | Size of an `.ENUM`/`.ARRAY`/`.STRUCT` label in bytes (1..4) |
| `dta b(rnd(min,max,length))` | Assemble-time random byte table (the pseudo-command is `RND(min,max,length)`, used inside `DTA`) |

### Conditional assembly

```asm
.IFDEF    label           ; true if label is defined
.IFNDEF   label           ; true if undefined
.IF       expr            ; assembly if expr ≠ 0
.ELSE                    ; alternative branch
.ELSEIF   expr           ; chained condition (aliases: IFT/ELS/ELI/EIF)
.ENDIF                   ; end conditional block
```

### Repeat loops

```
.REPT expression [,parameter1, parameter2, ...]   ; block repeat
  label:1  mva #0 $d012+#     ; :1 = parameter, # (or .R) = loop counter
.ENDR

.REPT 5, $12,$33,$44,$55,$66 ; parameters are evaluated before substitution
  dta :1,:2,:3,:4,:5
.ENDR
```

Single-line repeat uses the `:` operator: `:4 asl @`, `:256 dta #/8`, `ladr :4 dta l(line:1)`. In a macro, write `:+4` (any non-digit after the colon) so `:` is read as the repeat count rather than parameter 4.

### Zero-page variables and multiple passes

MADS is a multi-pass assembler, so a forward-referenced label known to be in `$00-$FF` gets zero-page addressing (`lda tmp+1` becomes `A5 xx`); use `lda.w` or `dta {lda $00},$80` to force absolute/zp explicitly. `ORG $20,$3080` assembles at `$0020` with load address `$3080` for code that will be copied into page zero.

Zero-page scratch areas are declared, not guessed: `.ZPVAR a,b,c .word = $80` allocates consecutive ZP variables (default start `$0080`), `.VAR`/`.ZPVAR` addresses are assigned at the end of the enclosing block (`.ENDP`/`.ENDL`/`.END`), and reusing an address warns (*Access violations at address $xxxx*).


---
