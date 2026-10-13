# Base Map

## 2.1  Full 64 K Memory Map ($0000 – $FFFF)

The Atari 8-bit has a flat 64 K CPU address space. Which ROM or RAM is visible in some ranges depends on the machine family and, on XL/XE machines, `PORTB ($D301)`.

### Map by region

| Region | Purpose |
|---|---|
| `$0000-$00FF` | Zero page — OS variables, DOS/BASIC work areas, user-reserved bytes if your environment allows them |
| `$0100-$01FF` | Hardware stack |
| `$0200-$02FF` | OS page 2 shadows, vectors, timers, color registers, keyboard/display variables |
| `$0300-$03FF` | OS page 3 tables and work areas (`HATABS`, `IOCB`s, buffers) |
| `$0400-$7FFF` | Main RAM; on 130XE-class machines `$4000-$7FFF` can be replaced by banked extended RAM |
| `$8000-$9FFF` | Cartridge window (`RD4` / right or lower 8K) |
| `$A000-$BFFF` | BASIC ROM, cartridge window (`RD5` / left or upper 8K), or RAM depending on machine and banking |
| `$C000-$CFFF` | XL/XE OS ROM or underlying RAM when OS ROM is banked out |
| `$D000-$D0FF` | GTIA |
| `$D100-$D1FF` | PBI device select / status / device space |
| `$D200-$D2FF` | POKEY |
| `$D300-$D3FF` | PIA 6520 |
| `$D400-$D4FF` | ANTIC |
| `$D500-$D5FF` | Cartridge control space (`CCTL`) |
| `$D600-$D7FF` | PBI/ECI device register space |
| `$D800-$FFFF` | Math Pack and OS ROM on computer models unless overlaid / banked out |

### Common zero-page / page-2 / page-3 landmarks

| Address | Name | Purpose |
|---|---|---|
| `$0008` | `WARMST` | Warm-start flag |
| `$000A/$000B` | `DOSVEC` | DOS entry vector |
| `$000C/$000D` | `DOSINI` | DOS initialization vector |
| `$000E/$000F` | `APPMHI` | Application memory high-water mark |
| `$0012-$0014` | `RTCLOK` | 24-bit real-time clock |
| `$0042` | `CRITIC` | Critical I/O section flag |
| `$004D-$004F` | `ATRACT/DRKMSK/COLRSH` | Attract-mode state |
| `$006A` | `RAMTOP` | Top of RAM in pages |
| `$0200/$0201` | `VDSLST` | DLI vector |
| `$0222/$0223` | `VVBLKI` | Immediate VBI vector |
| `$0224/$0225` | `VVBLKD` | Deferred VBI vector |
| `$022F` | `SDMCTL` | ANTIC DMA shadow |
| `$0230/$0231` | `SDLSTL/SDLSTH` | Display list pointer shadow |
| `$0244` | `COLDST` | Cold-start flag |
| `$02C4-$02C8` | `COLOR0-COLOR4` | Color shadows |
| `$02E0/$02E1` | `RUNAD` | Binary load run address |
| `$02E2/$02E3` | `INITAD` | Binary load init address |
| `$02E5/$02E6` | `MEMTOP` | Top of usable RAM pointer |
| `$02FC` | `CH` | Keyboard character buffer |
| `$031A` | `HATABS` | Device handler table |
| `$0340-$03BF` | `IOCB0-IOCB7` | Eight 16-byte I/O control blocks |

### PIA 6520 (Peripheral Interface Adapter)

Address range: `$D300-$D3FF`; only the low two address bits are decoded, so the four PIA registers repeat throughout the page.

| Register | Address | Function |
|---|---|---|
| `PORTA` | `$D300` | Joystick directions for ports 1 and 2; with PACTL bit 2 clear, accesses DDRA instead |
| `PORTB` | `$D301` | Joystick directions for ports 3 and 4 on 400/800; ROM/RAM/bank control on XL/XE; with PBCTL bit 2 clear, accesses DDRB instead |
| `PACTL` | `$D302` | Port A control register |
| `PBCTL` | `$D303` | Port B control register |

---
