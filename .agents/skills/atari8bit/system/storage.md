---
name: atari8bit-disk-file
description: >-
  Atari 8-bit SIO frame protocol, 810/1050/XF551/Indus GT drive commands, XEX/ATR/IOCB formats, SpartaDOS X, xBIOS mini-OS file access.
---

# 07 — Disk Drives & File I/O

> **Key items:** SIO DCB fields; Status byte C/E/A/N; DDEVIC/DUNIT/DCMD; IOCB $0340
> **Scope:** SIO frame format, disk drive commands, XEX/ATR binary formats, IOCB, SpartaDOS X relocatable, xBIOS

---

## Quick-lookup

| Need | See § |
|---|---|
| SIO frame format table | §7.1 |
| Drive commands (810/1050/XF551/Indus GT) | §7.2 |
| IOCB structure + free-IOCB-finder snippet | §7.3 |
| XEX binary format header table | §7.4 |
| ATR virtual disk format block structure | §7.5 |
| SDX binary block types ($FFFA/$FFFE/$FFFD/$FFFB) | §7.6 |
| **xBIOS mini-OS file access** | §7.7 |
| Boot/custom loader patterns | §7.9 |
| SIO checksum and peripheral-side protocol | §7.10 |
| DSKINV disk-driver entry | §7.11 |
| DOS/SDX command-line parsing | §7.12 |
| CIO special command numbers | §7.13 |

---

## §7.1  SIO Serial I/O

> ⚠ **SIO timeout:** Each SIO phase is time-limited: SIO arms a countdown timer (derived from the DCB timeout `DTIMLO` and the handler's own limits) and returns a timeout error (`$8A`) if the device never answers. A silent device therefore fails the call instead of hanging it — check `DSTATS` ($0303) after every SIO call before reusing the DCB, and never retry-loop on a dead channel.

> ⚠ **IOCB status discipline:** After CIO calls, always check the returned status before consuming data or reusing the IOCB. Poll loops that treat any nonzero status as success can race device-handler transitions and lose data.

### Frame format

```
[LEADER] [DEVICE_ID (1)] [COMMAND_FRAME] [ACK/NACK] [DATA_FRAME(s)] [STATUS_FRAME]
```

| Field | Value |
|---|---|
| Device ID | Unit address: $31–$3F disk (D1:–D8: = $31–$38), $40–$4F printer, $60 cassette, $70+ third-party |
| Leader | A run of `$55` bytes; the frame begins at the first byte that is not `$55` |
| COMMAND frame | 5 bytes: Device ID + command byte + AUX1 + AUX2 + checksum, sent while COMMAND is asserted low |
| ACK/NACK | 1 byte from the device: ACK `$41` (`'A'`) or NAK `$4E` (`'N'`) |
| DATA frame | Data bytes + one-byte checksum |
| STATUS | One byte from the device at the end of the operation: COMPLETE `$43` (`'C'`) or ERROR `$45` (`'E'`) |

The selected device answers the command frame with ACK (`$41`); NAK (`$4E`) or silence means the frame was rejected. The receiving side acknowledges each data frame the same way, and a finished operation ends with a single status byte, COMPLETE (`$43`) or ERROR (`$45`).

### SIO checksum

Every SIO command and data block ends with a one-byte checksum. The checksum
is the end-around-carry sum of all bytes in the block, excluding the checksum
byte itself: add each byte, and when the addition overflows past `$FF`, add
the carry back into the low byte.

```asm
        ldx #$00
        stx CHKSUM
        clc
?loop   lda DATA,x
        adc CHKSUM
        adc #$00        ; fold carry back into the 8-bit sum
        sta CHKSUM
        inx
        bne ?loop       ; 256-byte block
```

Use the same calculation for command frames and data frames. Custom
peripherals should verify the command checksum before ACKing the command,
then verify the data-frame checksum before sending final COMPLETE/ERROR.

---

## §7.2  Disk Drives (810 / 1050 / XF551 / Indus GT)

| Drive | Key features |
|---|---|
| 810 | WD1771 FDC; single density (FM), 128-byte sectors, 90 KB |
| 1050 | Single + enhanced density (130 KB); 256-byte sectors need a US Doubler-class ROM; single-sided |
| XF551 | Double density (MFM), 256-byte sectors, 360 KB double-sided |
| Indus GT | Double density, 180 KB single-sided; compatible with the standard SIO disk commands |

The drive's SIO address goes in `DDEVIC` ($31 for D1:, $32 for D2:, …) and the drive number in `DUNIT`.

---

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

---

## §7.4  XEX Binary Load Format

| Field | Magic |
|---|---|
| Block 1 header | `FF FF` (standard Atari binary load file) |
| Segment header | start_lo start_hi end_lo end_hi, inclusive |
| INIT vector | segment writes `$02E2/$02E3`; DOS calls it after loading that segment |
| RUN vector | segment writes `$02E0/$02E1`; DOS jumps there after loading completes |

XEX files are the native Atari binary format. A file may contain several load segments. `$FF $FF` is a marker, not a universal per-block command byte; after it, the loader expects start/end address pairs and raw bytes. DOS 2.x refuses segments that load below `$0700` (the DOS/MEMLO area), so a normal executable's first segment starts at `$0700` or above. For reversing, build a segment map and watch writes to `INITAD ($02E2)` and `RUNAD ($02E0)`.

---

## §7.5  ATR Virtual Disk Format

| Field | Value |
|---|---|
| ATR magic | `$96 $02` (little-endian `$0296`); the header is 16 bytes |
| Paragraph count | Word at +2: image size in 16-byte paragraphs, excluding the 16-byte header (high word at +6) |
| Sector size | Word at +4: 128 bytes (SD) or 256 bytes (DD); `0` = unknown |
| Sector count | `(file size − 16) / sector_size`; when the sector size is 256 the three boot sectors are normally 128 bytes each, giving `(file size − 400) / 256 + 3` |

Boot and loader notes:

- When the sector size is 256, the first three (boot) sectors are usually stored as 128 bytes each, as on enhanced-density images.
- Boot disks may load code before any DOS filesystem is active.
- Custom loaders often bypass CIO and call `SIOV` with direct sector commands.
- Directory entries are DOS-dependent; do not infer MyDOS/SpartaDOS/DOS 2.x layout without identifying the DOS.

---

## §7.6  SpartaDOS X Relocatable Code

SDX strips binary into relocatable blocks. The block header types:

```
*dta a($FFFF),a(str_adr),a(end_adr)   ; non-relocatable binary block (standard DOS)
*dta a($FFFA),a(str_adr),a(end_adr)   ; SDX non-relocatable (identifies SDX loader)
*dta a($FFFE),b(blk_num),b(blk_id)
          a(blk_off),a(blk_len)       ; relocatable block
*dta a($FFFD),b(blk_num),a(blk_len)   ; address-update block
*dta a($FFFB),c'SMB_NAME',a(blk_len)  ; symbol update block
*dta a($FFFC),b(blk_num),a(smb_off)
          c'SMB_NAME'                 ; definition block (new symbol)
```

`blk_id` bits: bits 1–5 = memory type ($00=main RAM, $02=ext RAM/RAMBO); bit 7 = absence-of-data flag. The SDX loader computes `new_addr = block_addr_abs + (loaded_addr − blk_off)` for every address field in the relocatable block.

---

## §7.7  xBIOS — Mini-OS File Access

xBIOS is a small resident I/O module that loads and saves files without a DOS. Its loader reads a configuration (including the `XAUTORUN` file) from disk, the module normally lives at `$0800`, and it is called through a vector table — `OPEN_FILE`, `LOAD_DATA`, `WRITE_DATA`, `LOAD_BINARY_FILE`, `READ_SECTOR`, directory entry calls, and so on at `$0800+$03`, `$0800+$06`, `$0800+$09`, ….

**What xBIOS provides:** open, load, read/write bytes, seek (file offset), sector reads and directory scanning. It keeps its own DCB-like variables (`xDEVICE`, `xDCMD`, `xDAUX1/2`, buffer pointer) inside its memory area and drives the standard SIO layer below.

**Limitations:** it cannot create new files or directories, and cannot extend an existing file.

**DCB layout for direct SIO access:** the DCB is fixed at `$0300` (not zero page); offsets from it are `$00` DDEVIC, `$01` DUNIT, `$02` DCOMND, `$03` DSTATS, `$04` DBUFLO/HI, `$06` DTIMLO, `$08` DBYTLO/HI, `$0A` DAUX1/2.

```asm
                ; standard DCB init for a sector READ
dcb_dev     = $0300         ; DDEVIC — SIO device ID (e.g. $31 for drive 1)
dcb_unit    = $0301         ; DUNIT  — drive number (1-8)
dcb_cmd     = $0302         ; DCOMND — $52 = read sector
dcb_stats   = $0303         ; DSTATS — $40 = read into buffer, $80 = write
dcb_buf     = $0304         ; DBUFLO/DBUFHI — buffer address
dcb_tim     = $0306         ; DTIMLO — timeout
dcb_len     = $0308         ; DBYTLO/DBYTHI — byte count
dcb_aux     = $030a         ; DAUX1/DAUX2 — sector number

        lda #$31               ; DDEVIC = drive 1
        sta dcb_dev
        lda #1
        sta dcb_unit
        lda #$52               ; DCOMND = $52 (read sector)
        sta dcb_cmd
        lda #$40               ; DSTATS = transfer from device to computer
        sta dcb_stats
        mwa #read_buffer dcb_buf
        lda #$80               ; DBYT = 128 bytes
        sta dcb_len
        lda #0
        sta dcb_len+1
        mwa #sector dcb_aux    ; DAUX1/2 = sector number

        jsr SIOV               ; $E459 — call SIO handler via OS vector
        cpy #$01               ; Y = status: $01 = success
        bne ?error
        ; ... read_buffer now holds the sector
?error  rts

; read_buffer must be sector-aligned: 128 bytes for SD disks (Atari 810 format)
```

**xBIOS vs native CIO:** CIO is the OS-level handler layer (`CIOV`); SIO is the serial-bus layer (`SIOV`). xBIOS bypasses standard DOS file handling and calls SIO through its own vectors and buffer variables.

---

---

## §7.8 Loader and Depacker Reversing Notes

Use this section with `tooling/reversing.md`.

| Symptom | Likely meaning |
|---|---|
| `SIOV` calls with changing AUX sector numbers | Direct sector loader |
| Writes to `RUNAD` or final indirect `JMP` | Loader transfers to real program |
| `(src),y` and `(dst),y` stream loops | Copy/depack stub |
| Bit-buffer shifts through carry | LZ/DEFLATE-style token reader |
| Writes to `$D301` around `$4000-$7FFF` copies | Extended RAM/banked asset transfer |
| CIO `D:` opens only during init | DOS file load before custom runtime |

Minimum reverse output:

- sector/file source;
- destination address range;
- final entry point;
- whether OS/DOS vectors are restored;
- whether the loader requires a specific DOS, drive, or SIO timing.

## §7.9 Loader Patterns

Boot-sector loaders run before DOS file APIs are active. They normally use
the OS disk entry or direct `SIOV` calls to read sectors into memory:

```asm
        org $0700
boot_hdr
        .word $0001             ; number of boot sectors to load (1-255)
        .word boot_hdr          ; load address of the boot block
        .word $ffff             ; init/entry address ($ffff = none)

        lda #$ff
        sta $d301               ; disable BASIC / map RAM on XL/XE
        lda #1
        sta $0301               ; DUNIT = drive 1
        lda #'R'
        sta $0302               ; DCMD = read
        mwa #main_start $0304   ; DBUF
        mwa #main_sector $030a  ; DAUX sector number

load    jsr $e453               ; DSKINV ($E459 = SIOV)
        bmi error               ; negative status in Y
        adw $0304 #$80          ; next 128-byte buffer
        inw $030a               ; next sector
        ; decrement sector counter...
        jmp load
error   jmp $e477               ; COLDSV — cold start (reboot)
```

Use this only for ATR/boot-disk workflows. DOS file APIs are not active yet,
and the first three boot sectors are normally 128 bytes even on
enhanced-density disks.

Dual-address loader stub:

```asm
source = $2000
dest   = $0700

        org source
        ; copy several pages from source to dest, then jump dest

        org dest,source         ; run as if at dest, store bytes at source
go      ; code that expects to execute at dest
```

This MADS `ORG run,load` form is the correct way to write self-relocating loaders: labels resolve to the execution address, while the bytes are emitted for the file/load address. When reversing, look for early copy loops followed by `JMP dest`; the real code addresses are usually the second `ORG` operand, not the initial file segment address.

For analyzer tools, read 16-bit block headers, distinguish standard XEX
segments from `$FFFA-$FFFE` SDX control blocks, and report update/symbol
records rather than flattening the file into raw load ranges.

## §7.10 SIO Peripheral-Side Protocol

A custom SIO peripheral sees a command phase followed by an optional data
phase. A command frame has:

| Byte | Meaning |
|---|---|
| 0 | Device ID and unit |
| 1 | Command byte |
| 2 | `DAUX1` |
| 3 | `DAUX2` |
| 4 | Checksum |

For a write-style command:

1. Wait for SIO COMMAND asserted.
2. Receive the 4-byte command plus checksum.
3. Wait for COMMAND deasserted.
4. If device ID, command, and checksum match, send ACK (`'A'`); otherwise send NAK (`'N'`).
5. Receive the data frame plus checksum.
6. ACK or NAK the data frame.
7. Perform the operation.
8. Send COMPLETE (`'C'`) or ERROR (`'E'`).

Common timing in simple microcontroller implementations is about 1000 us
before ACK/NAK and about 250 us before COMPLETE/ERROR. Treat these as
conservative software delays, not proof that all devices can collapse timing.

## §7.11 DSKINV Disk-Driver Entry

`DSKINV` is the OS disk-driver entry at `$E453`. It fills standard DCB fields
for basic disk operations and then uses `SIOV ($E459)`. Status is returned in
`DSTATS ($0303)` and in `Y`; negative status (`N=1`) means error.

The disk driver uses:

| Variable | Address | Purpose |
|---|---|---|
| `DSKTIM` | `$0246` | Long timeout, mainly formatting |
| `DSCTLN` | `$02D5/$02D6` | Sector size |
| `DCOMND` | `$0302` | Requested disk command |

Supported direct commands:

| Command | Meaning |
|---|---|
| `$21` / `'!'` | format disk |
| `$22` / `'"'` | format disk using the parameters in AUX1/AUX2 |
| `$4E` / `'N'` | read the PERCOM block (drive configuration) |
| `$4F` / `'O'` | write the PERCOM block |
| `$50` / `'P'` | put sector without verification |
| `$52` / `'R'` | read sector |
| `$53` / `'S'` | read status |
| `$57` / `'W'` | write sector with verification |

`DSKINV` only sets up these commands; anything else (for example the
double-density `$D0–$D5` commands of third-party drives) needs a manually
prepared DCB and a direct `SIOV` call.

Read/write sector setup:

```asm
        lda #1
        sta DUNIT
        lda #'R'        ; or 'P' / 'W'
        sta DCOMND
        ldx #<buffer
        ldy #>buffer
        stx DBUF
        sty DBUF+1
        ldx #<sector
        ldy #>sector
        stx DAUX1
        sty DAUX2
        jsr DSKINV
        bmi error
```

The status command sets `DSTATS` ($0303) to `$40`, `DBYT` to 4 and `DBUF` to
`DVSTAT ($02EA)`, where the four status bytes are stored. Formatting uses
`DSKTIM`; after a format, the buffer receives a list of bad sector numbers
ending with `$FFFF`, and `DBYT` is set to the list length excluding the
terminator.

## §7.12 DOS and SpartaDOS X Command Lines

Several DOSes expose command-line parameter retrieval through the OSS/DOS XL
protocol. Detect it by checking that DOS is loaded, `DOSVEC ($000A)` points
below ROM, and `(DOSVEC)+3` contains opcode `$4C` (`JMP`). The callable
parameter reader is at `(DOSVEC)+3`.

The parameter reader copies the next parameter into the DOS's command-name
buffer, `COMFNAM`. The returned string starts with a device name and ends with
EOL `$9B`. The routine does not by itself report end-of-line; compare the buffer
offset before and after the call to detect that no more parameters were
consumed.

SpartaDOS X also provides a richer parsing library:

- `U_SLASH` parses a group of adjacent slash switches as a set, not as a
  sequence of separate ordered tokens.
- `/X /A 23 /Q`, `/XA 23 /Q`, and `/AX 23 /Q` can be equivalent to
  `U_SLASH` for switch detection.
- If a switch such as `/A` requires the following numeric parameter, check
  which switch occurred last before calling `U_GETNUM`.
- In SDX 4.47 and later, `U_SLASH` returns the ATASCII code of the last
  switch in `A`.
- SDX command lines are limited to 64 characters. For persistent option
  sets, parse an environment variable first, then restore and parse the real
  command line.

Environment-variable parse pattern:

1. Save `LBUF` and `BUFOFF`.
2. Call `GETENV` for the variable name.
3. Copy the returned text from the floating-point buffer area to `LBUF`.
4. Set `BUFOFF` to zero and run the same parser used for command-line text.
5. Restore the saved `LBUF` and `BUFOFF`.
6. Parse the actual command-line arguments.

The environment-variable text is constrained by the same 64-character command
buffer limit.

## §7.13 CIO Special Commands by Device

CIO special commands are device-handler specific. Do not assume a command
number has the same meaning across `D:`, `E:`, `P:`, and `S:`.

Common `D:` special commands:

| CMD | Meaning on common DOS handlers |
|---|---|
| `$20` / 32 | rename file |
| `$21` / 33 | delete file |
| `$22` / 34 | DOS-dependent: unerase, lock disk, make directory, or unsupported |
| `$23` / 35 | lock file or directory |
| `$24` / 36 | unlock file or directory |
| `$25` / 37 | POINT / seek |
| `$26` / 38 | NOTE / tell |
| `$27` / 39 | DOS-dependent: get file length or binary load |
| `$28` / 40 | binary load on many DOSes |
| `$29` / 41 | DOS-dependent: binary save, set current directory, or pick directory |
| `$2A` / 42 | make directory |
| `$2B` / 43 | remove directory |
| `$2C` / 44 | change directory |
| `$2D` / 45 | set boot file |
| `$2F` / 47 | get disk info |
| `$30` / 48 | get current directory |
| `$31` / 49 | set attributes on SpartaDOS X-style handlers |
| `$FE` / 254 | format disk on common DOSes |

`E:` and `P:` have no standard special commands, but the XEP80's `E:` handler
adds device-specific ones (for example switching 80-column mode on and off and
controlling burst transmit). Treat those numbers as handler-specific and verify
them against the handler in use.

The graphics-screen `S:` handler implements:

| CMD | Meaning |
|---|---|
| `$11` / 17 | `DRAWTO` using `CRSCOL`, `CRSROW`, and `ATACHR` |
| `$12` / 18 | `FILLTO`, like `DRAWTO` plus horizontal fill using `FILDAT` |

When writing portable DOS code, gate special commands by DOS/handler
detection. If the command is not supported, expect a device error rather than
quiet no-op behavior.
