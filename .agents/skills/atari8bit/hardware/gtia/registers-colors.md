# Registers Colors

## §4.1  Register Map (`$D000-$D01F`)

GTIA uses many **dual-purpose addresses**: reading and writing the same address
often means different registers. Do not read hardware registers expecting to get
back the last value written.

| Addr | Read | Write | OS shadow | Notes |
|---|---|---|---|---|
| `$D000` | `M0PF` | `HPOSP0` | — | Missile 0 ↔ playfield / player 0 X |
| `$D001` | `M1PF` | `HPOSP1` | — | Missile 1 ↔ playfield / player 1 X |
| `$D002` | `M2PF` | `HPOSP2` | — | Missile 2 ↔ playfield / player 2 X |
| `$D003` | `M3PF` | `HPOSP3` | — | Missile 3 ↔ playfield / player 3 X |
| `$D004` | `P0PF` | `HPOSM0` | — | Player 0 ↔ playfield / missile 0 X |
| `$D005` | `P1PF` | `HPOSM1` | — | Player 1 ↔ playfield / missile 1 X |
| `$D006` | `P2PF` | `HPOSM2` | — | Player 2 ↔ playfield / missile 2 X |
| `$D007` | `P3PF` | `HPOSM3` | — | Player 3 ↔ playfield / missile 3 X |
| `$D008` | `M0PL` | `SIZEP0` | — | Missile 0 ↔ players / player 0 width |
| `$D009` | `M1PL` | `SIZEP1` | — | Missile 1 ↔ players / player 1 width |
| `$D00A` | `M2PL` | `SIZEP2` | — | Missile 2 ↔ players / player 2 width |
| `$D00B` | `M3PL` | `SIZEP3` | — | Missile 3 ↔ players / player 3 width |
| `$D00C` | `P0PL` | `SIZEM` | — | Player 0 ↔ players / packed missile widths |
| `$D00D` | `P1PL` | `GRAFP0` | — | Player 1 ↔ players / player 0 graphics |
| `$D00E` | `P2PL` | `GRAFP1` | — | Player 2 ↔ players / player 1 graphics |
| `$D00F` | `P3PL` | `GRAFP2` | — | Player 3 ↔ players / player 2 graphics |
| `$D010` | `TRIG0` | `GRAFP3` | `STRIG0 $0284` | Joystick 0 trigger / player 3 graphics |
| `$D011` | `TRIG1` | `GRAFM` | `STRIG1 $0285` | Joystick 1 trigger / missile graphics |
| `$D012` | `TRIG2` | `COLPM0` | `PCOLOR0 $02C0` | Joystick 2 trigger / player+missile 0 colour |
| `$D013` | `TRIG3` | `COLPM1` | `PCOLOR1 $02C1` | Joystick 3 trigger / player+missile 1 colour |
| `$D014` | `PAL` | `COLPM2` | `PCOLOR2 $02C2` | PAL flag / player+missile 2 colour |
| `$D015` | — | `COLPM3` | `PCOLOR3 $02C3` | Player+missile 3 colour |
| `$D016` | — | `COLPF0` | `COLOR0 $02C4` | Playfield colour 0 |
| `$D017` | — | `COLPF1` | `COLOR1 $02C5` | Playfield colour 1 |
| `$D018` | — | `COLPF2` | `COLOR2 $02C6` | Playfield colour 2 |
| `$D019` | — | `COLPF3` | `COLOR3 $02C7` | Playfield colour 3 |
| `$D01A` | — | `COLBK` | `COLOR4 $02C8` | Background / border colour |
| `$D01B` | — | `PRIOR` | `GPRIOR $026F` | Priority, fifth player, player-overlap, GTIA modes |
| `$D01C` | — | `VDELAY` | — | Per-object one-scan-line vertical delay |
| `$D01D` | — | `GRACTL` | — | PMG display enable and trigger latches |
| `$D01E` | — | `HITCLR` | — | Clear all PMG collision latches |
| `$D01F` | `CONSOL` | `CONSPK` | — | Console keys / speaker click |

## §4.2  Player / Missile Coordinates and Sizes

- Visible PMG pixels are normally in horizontal color-clock range
  `$22-$DD` (34-221 decimal).
- Setting HPOS to `0`, or to `$DE` and above, keeps the object off-screen.
- Player width register values:
  - `$00` = normal width
  - `$01` = double width
  - `$02` = same as normal
  - `$03` = quadruple width
- `SIZEM` packs four 2-bit missile widths in the same encoding. Missiles are
  2 color clocks wide at normal width, 4 at double, and 8 at quadruple.

## §4.3  Colour Registers and Palette Model

GTIA colour registers are 8-bit values:

| Bits | Meaning |
|---|---|
| 7-4 | hue / chroma |
| 3-0 | luminance |

In the normal CTIA/GTIA colour interpretation, the least-significant luminance
bit is not observed, so the practical palette is **16 hues × 8 luminances =
128 colours**. GTIA mode 9 uses all 16 luminance steps for playfield pixels.

All nine visible colour registers have OS shadows:

- `PCOLOR0-$02C0` .. `PCOLOR3-$02C3` for `COLPM0-3`
- `COLOR0-$02C4` .. `COLOR4-$02C8` for `COLPF0-3` and `COLBK`

If the OS is running, write the shadow in ordinary frame code. Write the
hardware register directly only when you need an immediate same-frame effect,
such as in a DLI.

## §4.4  Hi-res Playfield Colour Rules

ANTIC modes 2, 3, and F are the half-color-clock hi-res modes.

- Within the playfield, **0 bits use `COLPF2`**.
- **1 bits use the hue of `COLPF2` and the luminance of `COLPF1`**.
- `COLBK` is the border colour around the playfield, not the playfield
  background itself.

That is why changing `COLPF1` in these modes changes only brightness, while
changing `COLPF2` changes the hue of both foreground and background.

## §4.5  GTIA Mode Summary

`PRIOR` bits 6-7 select the GTIA colour interpretation:

| `PRIOR` bits 7-6 | Mode | BASIC | Behaviour |
|---|---|---|---|
| `00` | Default | — | Normal CTIA/GTIA playfield colour rules |
| `01` (`$40`) | GTIA 9 | 9 | 16 luminances of the hue in `COLBK` |
| `10` (`$80`) | GTIA 10 | 10 | 9 colour-register choices on the playfield |
| `11` (`$C0`) | GTIA 11 | 11 | 15 hues at one luminance from `COLBK`, plus background |

More detail, collision caveats, and practical notes are in `gtia-modes.md`.
