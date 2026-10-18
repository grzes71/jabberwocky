---
name: atari8bit-crt-editor
description: >-
  Atari 8-bit ATASCII screen-code table, CIO GET/PUT/PRINT via CIOV, key scancodes, number-base on-screen rendering.
---

# 08 — CRT Editor & Screen I/O

> earlier coverage on CIO key input, text record editing, character output, string printing, and editor control codes (all summaries in inline reference)> **Scope:** ATASCII screen codes, CIO GET/PUT/PRINT, key scancodes, number-base conversion on screen
> **Key items:** ATASCII $1B/$9B/$7D/$7E/$7F; CIOV $E456; IOCB $0340; KBCODE; hex_lookup table
> **Scope:** ATASCII screen codes, CIO GET/PUT/PRINT, key scancodes, number-base conversion on screen

## Quick-lookup

| Need | See § |
|---|---|
| ATASCII screen codes table | §8.1 |
| IOCB table + CIO GET/PUT/PRINT boilerplate | §8.2 |
| RAW key scancode read (CH/KBCODE → ATASCII) | §8.3 |
| Binary-to-hex digit lookup | §8.4 |
| 16-bit decimal-to-screen with EOL $9B | §8.4 |

## 8.1 ATASCII Screen Code Table

ATASCII has 128 code points ($00–$7F); the values $80–$FF are the same glyphs in inverse video. The byte stored in screen RAM is an internal (screen) code, not ATASCII — the `E:` handler translates ATASCII on output with the mapping below.

**ATASCII to Screen Code Mapping:**

| ATASCII | Screen Codes |
|---|---|
| `$00..$1F` | `$40..$5F` |
| `$20..$5F` | `$00..$3F` |
| `$60..$7F` | `$60..$7F` |
| `$80..$9F` | `$C0..$DF` |
| `$A0..$DF` | `$80..$BF` |
| `$E0..$FF` | `$E0..$FF` |

**Control Characters (16 codes):**

| Code | Dec | Name | Behaviour |
|------|-----|------|-----------|
| `$1B` | 27 | ESCAPE | Disables interpretation of control characters (except EOL). Next char is printed raw. |
| `$1C` | 28 | CURSOR UP | Move cursor up. Wraps to bottom if at top. |
| `$1D` | 29 | CURSOR DOWN | Move cursor down. Wraps to top if at bottom. |
| `$1E` | 30 | CURSOR LEFT | Move cursor left. Wraps to right if at left edge. |
| `$1F` | 31 | CURSOR RIGHT | Move cursor right. Wraps to left if at right edge. |
| `$7D` | 125 | CLEAR | Clears screen and homes cursor to top-left. |
| `$7E` | 126 | BACKSPACE | Deletes char to the left of cursor and moves cursor left. |
| `$7F` | 127 | TAB | Moves cursor to next tab stop. |
| `$9B` | 155 | END OF LINE | Moves cursor to the start of the next line. |
| `$9C` | 156 | DELETE LINE | Deletes current logical line. Text below moves up. |
| `$9D` | 157 | INSERT LINE | Inserts blank line at cursor. Lines below move down. |
| `$9E` | 158 | CLEAR TAB | Clears tab stop at current cursor position. |
| `$9F` | 159 | SET TAB | Sets tab stop at current cursor position. |
| `$FD` | 253 | BELL | Generates a beep sound. |
| `$FE` | 254 | DELETE CHAR | Deletes char at cursor. Text to the right moves left. |
| `$FF` | 255 | INSERT CHAR | Inserts space at cursor. Text to the right moves right. |

**ANTIC encoding:** In the text modes (ANTIC modes 2 and 3) the screen byte is an 8-bit index into the character set; in the 4-color text modes (ANTIC modes 4–7) only the low 6 bits index the character set and the top 2 bits select the color. GTIA modes and the bitmap modes (Graphics 8/9/+) are different; see ANTIC display processor.

---

## 8.2 Keyboard & CRT Editor I/O (CIO)

CIO channels on XL/XE run through the IOCB table at `$0340` (IOCB0 starts at `$0340`, 16 bytes per channel; IOCB7 ends at `$03BF`). The OS opens `E:` (keyboard + screen editor, i.e. the `K:`/`E:` pair) on IOCB 0 at boot, so IOCB 0 needs no OPEN before reading keys or writing characters.

```asm
; --- CIO GET — read one character (E: is already open on IOCB #0) ---
        ldx    #$00               ; IOCB #0 = E: (keyboard/screen editor)
        lda    #$07               ; $07 = CIO GET CHARACTERS
        sta    $0342,x            ; ICCOM — command byte
        lda    #<char
        sta    $0344,x            ; ICBAL — buffer address low
        lda    #>char
        sta    $0345,x            ; ICBAH
        lda    #1
        sta    $0348,x            ; ICBLL — buffer length (1 byte)
        lda    #0
        sta    $0349,x            ; ICBLH
        jsr    CIOV               ; $E456 (XL/XE)
        bmi    ?err               ; negative = error
        lda    char               ; A = key in ATASCII

; --- CIO PUT — write one character to the screen (IOCB #0) ---
        lda    #$0B               ; $0B = CIO PUT CHARACTERS
        sta    $0342,x
        lda    #<char
        sta    $0344,x
        lda    #>char
        sta    $0345,x
        lda    #1
        sta    $0348,x
        lda    #0
        sta    $0349,x
        jsr    CIOV

; --- CIO PRINT — write a whole string plus EOL to the screen (IOCB #0) ---
        lda    #$0B               ; $0B = CIO PUT CHARACTERS
        sta    $0342,x
        lda    #<msg
        sta    $0344,x
        lda    #>msg
        sta    $0345,x
        lda    #<msg_end-msg      ; string length including the EOL
        sta    $0348,x
        lda    #>msg_end-msg
        sta    $0349,x
        jsr    CIOV
        ...
msg     .byte  "HELLO WORLD!",$9B

msg_end
```

**IOCB table (offsets from base `$0340 + N*16`):**

| Offset | Field | Notes |
|--------|-------|-------|
| `+0` | ICHID — handler index | `$FF` = channel free/closed |
| `+1` | ICDNO — device/unit number | e.g. unit 1 for D1: |
| `+2` | ICCOM — command | Write the verb here before CIOV |
| `+3` | ICSTA — status | Status of the last operation |
| `+4`/`+5` | ICBAL/ICBAH — buffer address | Where the character / data is stored |
| `+6`/`+7` | ICPTL/ICPTH | Handler's put-byte vector (set up by CIO) |
| `+8`/`+9` | ICBLL/ICBLH — buffer length | Byte count for GET/PUT |
| `+$A` | ICAX1 | Auxiliary 1 (the OPEN mode) |
| `+$B` | ICAX2 | Auxiliary 2 |

`CIOV` at `$E456` dispatches the command in `ICCOM` (`IOCB+2`): GET RECORD `$05` reads up to the next EOL into the buffer, GET CHARACTERS `$07` reads exactly the requested byte count.

---

## 8.3 Key Scancodes

POKEY latches the keyboard-matrix scan code from `KBCODE` ($D209), and the OS keyboard IRQ copies it to `CH` ($02FC) — that copy is what the `K:`/`E:` handlers translate into ATASCII via the key table. Raw scan codes are therefore only needed when bypassing CIO (full table in `system/input.md`):

```asm
        ; Raw key-code decode (no CIO)
        lda CH                  ; $02FC — scan code copied from KBCODE by the IRQ
        cmp #$FF                ; $FF = no key pending
        beq @no_key
        and #$3F                ; strip modifiers (bit 6 = SHIFT, bit 7 = CTRL)
        ; now A = base scancode 0-63; translate via the OS key table
```

---

## 8.4 Number Base On Screen

### Binary-to-hex digit

Convert the low nibble in A to a hex ATASCII digit. For direct screen-RAM writes subtract `$20` to get the internal code (`'A'` = $41 ATASCII → $21 internal); for output through CIO PUT use the ATASCII value as it is:

```asm
hex_lookup
        .byte  "0123456789ABCDEF"
to_ascii_hex
        and    #$0F             ; isolate nibble
        tax
        lda    hex_lookup,x     ; A = ATASCII '0'-'F'
        rts
```

### Decimal to screen (16-bit unsigned, right-aligned)

Result written to a 7-byte RAM buffer (6 digits + EOL ATASCII `$9B`) that is then handed to CIO PUT. Exercise the divide-by-10 routine from the math routines section §10:

```asm
; AX = 16-bit value; digits are produced least-significant first
dec_to_screen
        ldx    #5               ; pre-fill the 6-digit field with spaces
@next   lda    #$20
        sta    buffer,x
        dex
        bpl    @next
        ldy    #0               ; 0 = still suppressing leading zeros
        ldx    #5               ; index of the least significant digit
@loop   jsr    div_10_16        ; AX = AX / 10; A = remainder
        ora    #$30             ; digit → ATASCII '0'-'9'
        cpy    #0
        bne    @store           ; already printing significant digits
        cmp    #$30             ; leading zero → leave the space
        beq    @skip
        ldy    #1               ; first significant digit
@store  sta    buffer,x
@skip   dex
        bpl    @loop
        lda    #$9B             ; EOL
        sta    buffer+6
        rts

buffer  .byte  0,0,0,0,0,0,0    ; 6 digits + EOL, printed through CIO PUT
```

### Routine reference

Dividing a 16-bit value by 10: See math routines §10.2 (16-bit ÷10, 79 or 96 bytes depending on space/speed trade-off).

---

*Earlier coverage in this file:*
*ATASCII table §8.1; CIO GET/PUT/PRINT §8.2; scancodes §8.3; number base conversion §8.4.*
