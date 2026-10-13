# Xbios

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
