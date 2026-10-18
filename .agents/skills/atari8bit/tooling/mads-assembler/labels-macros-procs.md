# Labels Macros Procs

## 13.4 Labels and Scope

```asm
global_label              ; global by default (column 1)
.local local_area
local_label               ; local to local_area (column 1!)
?temporary                ; temporary: value may be redefined at any time
.endl
```

- Temporary labels (`?name`) can be reassigned anywhere, including with `+= -= ++ --`; `OPT ?+` turns `?name` into MAE-style *local* labels instead. Reach a label from an outer scope with a leading colon (`lda :label5`).
- `.LOCAL name` / `.ENDL` (alias `.LEND`) opens a scoped area; fields are addressed as `area.field` and `.USING area,field` imports one.
- Self-modifying labels: a label attached with `:` defines the label at the operand address, so the operand itself is the patch point.

```asm
        lda  label:#$40     ; LDA #$40      (label equ *-1)
        lda  src:$ff00,y    ; LDA $ff00,y   (src equ *-2)
        lda  temp::#$00     ; global-scope self-modification label (MADS 2.1+)
```

---

## 13.5 Macros (.MACRO/.ENDM)

```
name .MACRO [arg1,arg2,...] ['separator'] ["separator"]
     .MACRO name [(arg1,arg2,...)]
:1 :2 ... :argname        ; parameters, ":0"/"%%0" = number of parameters
.EXITM [.EXIT]            ; leave the macro body
.ENDM [.MEND]
```

- The parameter count is limited only by memory — there is no 9-parameter cap; parameters not passed come back as `-1` (`:0` reports how many were given).
- `['x']` declares the argument separator, `["x"]` additionally splits each argument into addressing mode + value.
- Anonymous labels inside a macro: `@+[0..9]` forward, `@-[0..9]` backward; without a number the occurrence is `0`.
- Every label defined in a macro is local (`LOOP::1` in the `.LAB` file). `.END` cannot close a macro.
- `name .DEFINE expr` (alias `.DEF`) creates a single-line macro whose expansion is used wherever the name appears; `.UNDEF name` disables such a definition again (any other name produces *Undeclared macro*).

```asm
.macro draw_bar color,xpos        ; arguments separated by ',' or space
        lda #:color               ; :color == :1
        sta COLPM0
        ldy #:xpos
@       sta (ptr),y               ; anonymous label starts in column 1
        iny
        bne @-                    ; nearest '@' backwards
.endm

        draw_bar 3,7              ; invocation
```

### Macro commands (built-in pseudo-ops)

| Macro command | Expansion semantics |
|---------------|-------------------|
| `MVA src,dst` | `LDA src / STA dst` (byte through A); `MVX`/`MVY` use X/Y |
| `MWA src,dst` | `LDA src / STA dst / LDA src+1 / STA dst+1` — low byte first; `MWX`/`MWY` use X/Y |
| `ADW a,b,c` | `CLC / LDA a / ADC b / STA c / LDA a+1 / ADC b+1 / STA c+1`; `ADW dst,#v` and `ADW dst,#v,dst` optimise a byte-sized `v` to `BCC/INC` |
| `SBW a,b,c` | `SEC / LDA a / SBC b / STA c / LDA a+1 / SBC b+1 / STA c+1` (byte-sized `b` optimises to `BCS/DEC`) |
| `ADD/SUB`, `ADB/SBB` | add/subtract without / with store to memory |
| `INW/DEW`, `INL/DEL`, `IND/DED` | increment/decrement a `.WORD`/`.LONG`/`.DWORD` in memory (the decrements clobber A) |
| `CPB/CPW/CPL/CPD` | compare `.BYTE`/`.WORD`/`.LONG`/`.DWORD`, most significant byte first |
| `PHR/PLR` | push/pull A, X and Y (`PHA/TXA/PHA/TYA/PHA`) |
| `REQ..RVS`, `SEQ..SVS`, `JEQ..JVS` | branch to the previous instruction, the next instruction, or a full 64 KB target (`JNE dest` = `BEQ *+4 / JMP dest`) |

`OPT R+` removes redundant loads/stores from consecutive `MVA/MVX/MVY/MWA/MWX/MWY` runs.

---

## 13.6 Procedures (.PROC/.ENDP)

```
name .PROC [(.TYPE par1,par2 .TYPE par3 ...)] [.REG] [.VAR]
.PROC name,address [(...)] [.REG] [.VAR]
.ENDP [.PEND] [.END]
```

- Parameter types: `.BYTE` (8) and `.WORD` (16) are relocatable, `.LONG` (24) and `.DWORD` (32) are not; `.STRUCT` parameters are not supported.
- `.REG` — parameter names must be built from the letters `A`, `X`, `Y` and at most three bytes can be passed. `.VAR` — the parameter names are the variables the arguments are stored in.
- Without `.REG`/`.VAR` the procedure uses the software stack and needs the `@CALL`/`@PUSH` (both in `@CALL.MAC`), `@PULL` and `@EXIT` macros plus `@PROC_VARS_ADR`/`@STACK_ADDRESS`/`@STACK_POINTER` (defaults `$0500`, `$0600`, `$FE`). `@EXIT` runs automatically at `.ENDP` to fix the stack pointer — it is not an early-return instruction.
- Arguments are passed as `#value`, a bare address, `@` (accumulator, `.BYTE` only, must be first) or `"label,x"`.

```asm
; .REG: parameter names must be A/X/Y
draw_line .PROC (.byte x,y) .REG
        stx current_x
        sty current_y
        rts
.endp

        draw_line #10,#20      ; register parameters

; .VAR (per-variable storage) with software stack
copy .PROC (.word src+1) .var
 .proc ToDst (.word src+1,dst+1) .var    ; nested .PROC = extra entry point
 .endp
        ldy #0
src     lda $ffff,y
dst     sta $ffff,y
        iny
        bne src
        rts
.endp

        copy.ToDst #$a080,#$b000   ; nested entry point
        copy       #$a360          ; default entry point
```

Labels inside a `.PROC` are local but reachable from outside as `proc.label` (`lda test.pole`); a leading `:` addresses an outer or global label, and `.def :name = value` defines one. Unreferenced procedures are skipped with `-x` (checked with `-vu`).

Nesting: `.PROC` blocks can be nested (this is how sub-procedure entry points such as `copy.ToDst` are created).
```
.proc outer
    .proc inner
    .endp
.endp
```

---
