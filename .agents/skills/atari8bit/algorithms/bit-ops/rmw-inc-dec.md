# Rmw Inc Dec

## 11.1 INC / DEC and Zero-Page Read-Modify-Write

### RMW on zero page

`INC <addr>` and `DEC <addr>` are single-operand instructions that read the byte,
add or subtract one, and write it back. The value wraps modulo 256 (`INC $FF`
gives `$00`, `DEC $00` gives `$FF`) and N/Z are set from the result:

```asm
zp_inc  equ $80
zp_dec  equ $81

        inc   zp_inc          ; +1, NZ flags set from result
        dec   zp_dec          ; -1, NZ flags set from result
```

On the NMOS 6502 the write-back happens **twice**: the dummy modify cycle
stores the unchanged value first, then the new value. On I/O registers that
double write is why such tricks work — and why `INC`/`DEC` must never be used on
a register whose write side effect is not intended.

### INC / DEC / LSR on NMIEN ($D40E)

`NMIEN` is write-only (`$80` = DLI enable, `$40` = VBI enable), and the read
performed by a read-modify-write instruction returns `$FF` on real hardware. So
the RMW result is derived from `$FF`, which gives three one-instruction ways to
change the NMI mask:

```asm
        inc   $d40e            ; writes $00 -> DLI and VBI disabled (block NMI)
        dec   $d40e            ; writes $FE -> DLI enabled only
        lsr   $d40e            ; writes $7F -> VBI enabled only
```

`INC $D40E` is the compact "block NMIs" idiom; `DEC $D40E` re-enables the DLI,
and `LSR $D40E` enables only the VBI. These depend on the floating-bus read value
and on the double write, so treat them as Atari-specific behaviour.

Do not confuse this with `NMIRES ($D40F)`: writing any value there **clears** the
latched NMI status bits (`NMIST`); it does not raise an NMI.

**Practical patterns:**
```asm
        inc   $d40e            ; block DLI/VBI
        dec   $d40e            ; allow DLI again
```

---
