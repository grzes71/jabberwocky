---
name: atari8bit-input
description: >-
  Atari 8-bit input device registers — joystick DB9 ports, STICK/TRIG/PADDL, light pen PENH/PENV, CONSOL keys, XEP80.
---

# 06 — Input Devices

> Supplementary code patterns for keyboard, joystick, paddle, mouse, light-pen, and console-key input. Content is self-contained.
> **Scope:** Joystick/paddle/trackball, mouse/tablet, light pen, XEP80, console keys
> **Key items:** STICK0-3 OS shadows $0278-$027B, PORTA/PORTB $D300/$D301, TRIG0-3 $D010-$D013, PADDL0-7 shadows $0270-$0277 / hardware $D200-$D207, CONSOL $D01F, PENH/PENV $D40C/$D40D

## Quick-lookup

| Need | See § |
|---|---|
| DB9 pinout and model port mapping | §6.0 |
| STICK OS shadows vs PIA hardware | §6.1 |
| TRIG per-trigger read | §6.1 |
| ROR joystick bit-field decoder | §6.1 |
| PADDLn RC-time; wait ≈228 cycles | §6.1 |
| Quadrature mouse nibble decoder | §6.1 |
| Light pen (PENH/PENV read + mapping) | §6.2 |
| CONSOL start/select/option + clear-to-write | §6.2 |
| XEP80 / Touch tablet | §6.2 |

## 6.0 DB9 Port and Model Mapping

The 9-pin controller port uses four digital direction lines, two analog paddle inputs, one trigger, +5V, and ground:

| Pin | Signal |
|---|---|
| 1-4 | Direction bits 0-3 |
| 5 | Paddle (pot) input |
| 6 | Trigger |
| 7 | +5V |
| 8 | Ground |
| 9 | Paddle (pot) input |

Logical port ownership:

| Port | Digital bits | Analog channels | Trigger |
|---|---|---|---|
| Joy 0 | PORTA bits 0-3 | POT0/POT1 | TRIG0 |
| Joy 1 | PORTA bits 4-7 | POT2/POT3 | TRIG1 |
| Joy 2 | PORTB bits 0-3 | POT4/POT5 | TRIG2 |
| Joy 3 | PORTB bits 4-7 | POT6/POT7 | TRIG3 |

XL/XE machines expose two controller ports; 400/800 machines expose four. On XL/XE, PORTB is also used for OS/BASIC/self-test/extended-RAM control, so do not assume ports 2-3 exist or that PORTB can be repurposed safely.

## 6.1 Joystick, Paddle & Mouse Registers

Joystick directions are read from the PIA ports, not from the GTIA `$D000` player-position registers. For OS-friendly code, read the VBI-updated shadows; for tight polling or unusual devices, read PIA directly.

| Register | Range | Purpose |
|---|---|---|
| STICK0-STICK3 | $0278-$027B | OS joystick direction shadows, active-low low nibble |
| PORTA | $D300 | Hardware directions for joystick ports 0-1 |
| PORTB | $D301 | Hardware directions for joystick ports 2-3 on 400/800; XL/XE ROM/RAM banking control |
| TRIG0-TRIG3 | $D010-$D013 | Per-trigger read, active low |
| CONSOL         | $D01F   | Console start/select/option keys |
| PADDL0-PADDL7 | $0270-$0277 | OS paddle shadows |
| POT0-POT7 | $D200-$D207 | Hardware paddle RC-time counters |

### Register map

| Register | Address | R/W | Description |
|---|---|---|---|
| `STICK0` | `$0278` | R | OS shadow for joystick 0 |
| `STICK1` | `$0279` | R | OS shadow for joystick 1 |
| `STICK2` | `$027A` | R | OS shadow for joystick 2 on 400/800 |
| `STICK3` | `$027B` | R | OS shadow for joystick 3 on 400/800 |
| `PORTA` | `$D300` | R/W | Hardware direction bits for ports 0-1 |
| `PORTB` | `$D301` | R/W | Hardware port 2-3 on 400/800; XL/XE banking register |
| `TRIG0`-`TRIG3` | `$D010`-`$D013` | R | Trigger inputs; `0` = pressed |
| `STRIG0`-`STRIG3` | `$0284`-`$0287` | R | OS trigger shadows; `0` = pressed |
| `PTRIG0`-`PTRIG7` | `$027C`-`$0283` | R | OS shadow of the paddle buttons; `0` = pressed |
| `CONSOL` | `$D01F` | R(W) | Console keys are active low; write any value to clear the speaker latch |
| `ALLPOT` | `$D208` | R | One bit per pot; a cleared bit means that pot's value is valid |

**STICK0 OS-shadow idiom**

For OS-friendly gameplay, read the VBI-maintained `STICKn` shadow once per frame and cache it for game logic:

```asm
stick_snapshot
        lda   STICK0           ; OS shadow at $0278
        and   #$0f             ; isolate active-low direction bits
        cmp   last_stick
        beq   ?unchanged
        jsr   stick_changed     ; process new directions
?unchanged
         rts
```

Direction bits in STICKn, active low:

      bit0 = UP   bit1 = DOWN   bit2 = LEFT   bit3 = RIGHT
      0 = active, 1 = inactive

For direct hardware polling of joystick 0, read `PORTA` and mask the low nibble. For joystick 1, read the high nibble and shift or compare in place.

```asm
stick_map
        lda PORTA
        and #$0f        ; joystick 0 active-low direction nibble
```

### ROR joystick bit-field decoder

`STICK0` (`$0278`) is an active-low bit field, not a Gray code. A cleared bit means the direction is pressed:

```
bit 0 = UP     bit 1 = DOWN
bit 2 = LEFT   bit 3 = RIGHT
```

Using `ROR` moves each direction bit into Carry, so a compact decoder can consume the four directions in order:

```asm
record_joystick
        lda   STICK0          ; $0278 OS shadow
        and   #$0f
        cmp   #$0f            ; centered: all direction bits high
        beq   ?none
        sta   latest_joystick
?none   lda   STRIG0          ; $0284 OS trigger shadow, 0 = pressed
        bne   ?done
        lda   #1
        sta   fire_pressed
?done   rts

process_joystick
        lda   #0
        sta   joystick_x
        sta   joystick_y

        lda   latest_joystick
        ror                   ; bit 0 -> Carry
        bcs   ?up_clear
        dec   joystick_y
?up_clear
        ror                   ; bit 1 -> Carry
        bcs   ?down_clear
        inc   joystick_y
?down_clear
        ror                   ; bit 2 -> Carry
        bcs   ?left_clear
        dec   joystick_x
?left_clear
        ror                   ; bit 3 -> Carry
        bcs   ?right_clear
        inc   joystick_x
?right_clear
        lda   #0
        sta   latest_joystick
        rts
```

For two-button joystick adapters that encode a second fire button through paddle timing, sample at the start of VBI: read `POT0`/`ALLPOT`, then write `POTGO` only after the read because `POTGO` resets the POT counters.

### Paddle reading (POT timing)

POT is an RC-integrator driven by a counter. Writing `POTGO ($D20B)` starts a scan and resets the counters, so read `POT0-POT7` first and trigger the next scan afterwards. In fast scan (`SKCTL` bit 2) the whole sequence takes two TV lines, so wait about 228 machine cycles before reading; in normal scan it takes about 228 scan lines, i.e. most of a frame, so poll the VBI-updated `PADDLn` shadows instead.

```asm
        ; fast scan: ~228 machine cycles (two TV lines) before POTn is valid
wait_paddle
        ldx   #45              ; 45 × 5 cycles ≈ 225 cycles, plus JSR/RTS
@loop   dex
        bne   @loop
        rts
```

XEP80: an SIO device with its own 80-column handler (`E:` plus special commands). Touch tablet (Atari CX77, X-Modern): read through a controller port as two analog axes plus a trigger.

### Trigger table

| Trigger | Address | R/W | Bit | Clear by write |
|---|---|---|---|---|
| TRIG0 | $D010 | R | b0 | no; read only |
| TRIG1 | $D011 | R | b0 | no; read only |
| TRIG2 | $D012 | R | b0 | no; read only |
| TRIG3 | $D013 | R | b0 | no; read only |

### Mouse, Trackball, Tablet Notes

- Atari Touch Tablet uses the analog paddle inputs: X on pin 9, Y on pin 5, button on pin 1 or trigger depending on mode.
- The CX-22 trackball and ST/Amiga mice present quadrature (direction/reference) pairs on the digital pins; treat them as edge/delta devices, not as absolute joystick states. The CX-80 trackball instead emulates joystick directions.
- Light gun trigger is on the trigger pin. Hardware notes describe reliable use on the fourth 400/800 port; XL/XE compatibility should be stated explicitly if required.

An ST/Amiga-style mouse puts one 2-bit Gray-code pair per axis on the port nibble (X on bits 0-1, Y on bits 2-3; the Amiga mouse drives the Y pair inverted). Sample the nibble at a rate higher than the mouse can move (once per VBI is enough for a cursor) and step by the signed delta for `(previous pair << 2) | new pair`:

```asm
; index = old_pair*4 + new_pair → signed step;
; a two-state jump (indices 2, 7, 8, 13) means a lost sample: treat it as 0
mouse_step
        .byte  0,  1,  0, -1
        .byte -1,  0,  1,  0
        .byte  0, -1,  0,  1
        .byte  1,  0, -1,  0

; add the signed step in A (-1/0/+1) to the 16-bit counter acc_lo/acc_hi
add_step
        bmi   ?minus
        beq   ?done            ; 0 → nothing to add
        inc   acc_lo           ; +1
        bne   ?done
        inc   acc_hi
        rts
?minus  lda   acc_lo
        bne   ?dec_lo          ; no borrow out of the low byte
        dec   acc_hi
?dec_lo dec   acc_lo
?done   rts
```

Poll the nibble at a fixed rate and accumulate the per-axis deltas: VBI-rate polling is usable for UI cursors; fast game movement should use a POKEY timer IRQ around 1 kHz and accumulate deltas for the frame.

---

## 6.2 Light Pen

Both registers latch when the pen's trigger is pulled low; the OS copies them into the shadows `PENH ($0234)` and `PENV ($0235)`.

`PENH ($D40C)`: horizontal position, counted in color clocks (values 0–227). The values do not line up 1:1 with screen columns — the visible area starts at 67 at the left and the count wraps through zero at the right edge — so normalise before use:

```asm
        lda   PENH
        cmp   #67
        bcs   ?norm            ; 67–227: still in the normal part of the line
        clc                    ; 0–66: wrapped past the right edge
        adc   #228
?norm   sec
        sbc   #67              ; → horizontal position from the left edge
        ...                     ; accept valid PENH
```

`PENV ($D40D)`: vertical position — the `VCOUNT` value at the time of the hit, i.e. two-line resolution. Screen rows read roughly 16 at the top to 111 at the bottom in this numbering; handle the `VCOUNT` wrap at the frame boundary.

## 6.3 Keyboard Input

Atari 8-bit computers read keyboard input through three primary paradigms: OS Shadow registers (polling-friendly), standard OS CIO calls (via the `K:` handler), or direct hardware scanning of POKEY registers (for games and bare-metal environments).

### 6.3.1 OS Shadow Register Polling
The OS copies every key it accepts into the `CH` shadow (and the locked modifiers into `SHFLOK`).

* **`CH ($02FC)`** (764): Keyboard code shadow. It holds the raw code copied from `KBCODE` (scan code plus any `$40` SHIFT / `$80` CTRL bits) or `$FF` when no new key is pending.
  > [!IMPORTANT]
  > Once a keypress is read from `CH`, you **MUST** reset it by writing `$FF` to `CH` so the OS knows the key has been processed.
* **`SHFLOK ($02BE)`** (702): Shift/Control lock flags — bit 6 (`$40`) = shift (caps) lock active, bit 7 (`$80`) = control lock active. Held modifier keys are not shadowed here: they appear as the `$40`/`$80` bits of `KBCODE`/`CH`.
* **`CRSINH ($02F0)`** (752): Cursor-inhibit flag — `0` = cursor displayed, non-zero = cursor hidden.

**Polling Zero-Page Shadow Example:**
```asm
poll_keyboard
        lda CH                 ; OS keyboard shadow at $02FC
        cmp #$FF               ; $FF = no keypress
        beq ?no_key
        
        pha                    ; save key code
        lda #$FF
        sta CH                 ; reset shadow code to acknowledge read
        pla                    ; restore key code
        
        ; ... process key in accumulator ...
?no_key rts
```

### 6.3.2 Direct Hardware Scanning (Bypassing OS)
For custom keyboard matrix decoding or when the OS ROM is disabled, POKEY registers are polled directly:

* **`KBCODE ($D209)`**: Holds the raw 8-bit keyboard matrix code.
  - Bits 0–5: Base raw scancode (0–63).
  - Bit 6: Shift modifier status (`1` = Shift is down / value + `$40`).
  - Bit 7: Control modifier status (`1` = Control is down / value + `$80`).
* **`SKSTAT ($D20F)`** (read side of SKCTL): Status register.
  - Bit 2: Key-down status (the last key is still pressed).
  - Bit 3: Shift key status.
  - Bit 5: Keyboard over-run — a key was pressed before the previous code was read. Bits 5–7 are error latches: they read as `1` when clear and are reset to `1` by a write to `SKRES ($D20A)`.
* **`SKCTL ($D20F)`**: Control register (Write-only).
  - Writing `$03` enables both the keyboard scanner and debounce logic (required for hardware polling). Bit 2 selects the fast pot scan.

**Direct Hardware Reading Example:**
```asm
; last_kbcode: separate byte holding the previous scan code (init to $FF)

init_keyboard_hardware
        lda #$03
        sta SKCTL              ; enable keyboard scan and debounce logic
        rts

poll_key_hardware
        lda KBCODE             ; $D209 — scan code latched with SHIFT/CTRL flags
        cmp last_kbcode
        beq ?nothing_new       ; unchanged → no new key
        sta last_kbcode
        rts                    ; A = new scan code (bit 6 = SHIFT, bit 7 = CTRL)
?nothing_new
        lda #$FF               ; return $FF indicating no new keypress
        rts
```

### 6.3.3 Keyboard Scancodes Mapping Table
The base raw scancodes (bits 0–5 of `KBCODE`/`CH`, unshifted and uncontrolled) map to keyboard keys as follows. The codes are not in keyboard order, and several codes have no key at all:

| Code | Key | Code | Key | Code | Key | Code | Key |
|---|---|---|---|---|---|---|---|
| `$00` | L | `$10` | V | `$20` | , | `$30` | 9 |
| `$01` | J | `$11` | HELP | `$21` | SPACE | `$31` | — |
| `$02` | ; | `$12` | C | `$22` | . | `$32` | 0 |
| `$03` | F1 (1200XL) | `$13` | F3 (1200XL) | `$23` | N | `$33` | 7 |
| `$04` | F2 (1200XL) | `$14` | F4 (1200XL) | `$24` | — | `$34` | BACKSPACE |
| `$05` | K | `$15` | B | `$25` | M | `$35` | 8 |
| `$06` | + | `$16` | X | `$26` | / | `$36` | < |
| `$07` | * | `$17` | Z | `$27` | INVERSE | `$37` | > |
| `$08` | O | `$18` | 4 | `$28` | R | `$38` | F |
| `$09` | — | `$19` | — | `$29` | — | `$39` | H |
| `$0A` | P | `$1A` | 3 | `$2A` | E | `$3A` | D |
| `$0B` | U | `$1B` | 6 | `$2B` | Y | `$3B` | — |
| `$0C` | RETURN | `$1C` | ESCAPE | `$2C` | TAB | `$3C` | CAPS LOCK |
| `$0D` | I | `$1D` | 5 | `$2D` | T | `$3D` | G |
| `$0E` | - | `$1E` | 2 | `$2E` | W | `$3E` | S |
| `$0F` | = | `$1F` | 1 | `$2F` | Q | `$3F` | A |

`—` = no key on most machines. F1–F4 exist only on the 1200XL; HELP, INVERSE and CAPS LOCK have no ATASCII character of their own — the OS key table returns the special codes `$80` (no character), `$81` (inverse toggle), `$82` (caps lock), and `$85` (Ctrl+3, EOF).

---

*All register maps, timing constants and code snippets are self-contained in this file; PIA port details in `system/memory-map.md`.*
