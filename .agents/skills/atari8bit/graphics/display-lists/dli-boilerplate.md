# Dli Boilerplate

## §1  Mandatory DLI Boilerplate

The shortest correct DLI that changes one hardware register:

```asm
my_dli
        pha                 ; save A
        txa
        pha                 ; save X
        tya
        pha                 ; save Y

        sta WSYNC           ; wait for end of current scan line
        lda #$0C
        sta COLPF0          ; $D016 — hardware, not $02C4

        pla
        tay
        pla
        tax
        pla
        rti                 ; pops P register from stack
```

**The RTI path:** the CPU vectors through `$FFFA/$FFFB`, the OS NMI handler
checks `NMIST`, and the DLI path jumps through `VDSLST ($0200/$0201)`.
`RTI` restores the processor status that was stacked on entry.

**Do not rely on A/X/Y surviving a DLI.** Save the registers you touch, write
hardware registers (not shadows), and return with `RTI`.

For multiple DLIs on one screen, either chain `VDSLST` from one handler to the
next or reset `VDSLST` from VBI each frame.
