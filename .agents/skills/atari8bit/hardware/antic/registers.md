# Registers

## 3.5  ANTIC Register Quick-Reference ($D400–$D40F)

All registers are at `$D4xx`; only the low 4 address bits are decoded, so they
repeat through the page.

| Register | Address | R/W | Description |
|---|---|---|---|
| DMACTL | `$D400` | W | DMA control: bits 0–1 = width (0=off/1=narrow/2=normal/3=wide); bit 2=missile DMA; bit 3=player DMA; bit 4=single-line PMG; bit 5=display-list/playfield DMA |
| CHACTL | `$D401` | W | Character control: bit 0=blank inverse characters; bit 1=inverse inverse characters; bit 2=vertical reflect |
| DLISTL | `$D402` | W | Display-list pointer low byte |
| DLISTH | `$D403` | W | Display-list pointer high byte |
| HSCROL | `$D404` | W | Horizontal fine scroll (low 4 bits) |
| VSCROL | `$D405` | W | Vertical fine scroll (low 4 bits) |
| PMBASE | `$D407` | W | Player/missile base page; 1 KB aligned in double-line mode, 2 KB aligned in single-line mode |
| CHBASE | `$D409` | W | Character-set base page; 1 KB alignment for modes 2–5, 512 B for modes 6/7 |
| WSYNC | `$D40A` | W | Wait for end of current scan line |
| VCOUNT | `$D40B` | R | Vertical line counter; returns actual scan line / 2 (0–130 NTSC, 0–155 PAL) |
| PENH | `$D40C` | R | Light-pen horizontal position |
| PENV | `$D40D` | R | Light-pen vertical position |
| NMIEN | `$D40E` | W | NMI enable: bit 5=RESET key interrupt, bit 6=VBI, bit 7=DLI |
| NMIRES | `$D40F` | W | Any write clears the NMIST status bits |
| NMIST | `$D40F` | R | NMI status: bit 5=RESET, bit 6=VBI, bit 7=DLI |

Shadow registers commonly used with OS running: SDMCTL=`$022F`, SDLSTL=`$0230/$0231`,
CHACT=`$02F3`, CHBAS=`$02F4`, VDSLST=`$0200/$0201`.
