# Cio File Access

## §7.3  IOCB File-Access (free-IOCB finder)

Finding a free IOCB: scan the handler-index byte (`ICHID`, offset `+0`) of each IOCB for `$FF` — CIO writes `$FF` there when a channel is closed. Each IOCB is 16 bytes, so that byte sits at `$0340/$0350/$0360…$03B0`.

```asm
; out: X = IOCB base offset ($00,$10,…,$70) — use $0340+X as the IOCB
;      Y negative ($A1) when no channel is free
find_free_iocb
        ldx #0                  ; IOCB offset (index × 16)
?loop   lda $340,x              ; ICHID: $FF = free (closed) channel
        cmp #$FF
        beq ?found
        txa
        clc
        adc #$10                ; next IOCB (16 bytes)
        tax
        cmp #$80                ; past IOCB 7 → none free
        bcs ?none
        jmp ?loop
?found  txa                     ; X = IOCB base
        rts
?none   ldy #-95                ; $A1: too many files (no free channel)
        rts
```

Alternative OS-style contract:

```asm
; out: N clear => X = IOCB offset ready to use, Y = channel number + 1
;      N set   => Y = -95 ($a1 — too many files/channels open)
lookup_iocb
        ldx   #$00
        ldy   #$01
@loop   lda   $0340,x           ; ICHID: $ff means a free (closed) channel
        cmp   #$ff
        beq   @found
        txa
        clc
        adc   #$10
        tax
        cmp   #$80              ; past IOCB 7?
        iny
        bcc   @loop
        ldy   #-95              ; TOO MANY CHANNELS OPEN
@found  rts
```

---
