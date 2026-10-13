# Collisions

## §4.8  Collision Detection

| Register | Read | Collision type |
|---|---|---|
| `$D000` / `M0PF` | Missile 0 ↔ playfield colours | Missile-to-playfield |
| `$D004` / `P0PF` | Player 0 ↔ playfield colours | Player-to-playfield |
| `$D008` / `M0PL` | Missile 0 ↔ players | Missile-to-player |
| `$D00C` / `P0PL` | Player 0 ↔ players | Player-to-player |

Important rules:

- Collision latches are **set in real time** as pixels are rendered.
- A set bit means “at least one collision occurred” since the last clear.
- There is **no missile-to-missile collision register**.
- Background colour does **not** register as a playfield collision.
- GTIA modes 9 and 11 disable playfield collisions; GTIA mode 10 only reports
  playfield collisions for pixels using `COLPF0-3`.

**Clear:** write any value to `HITCLR ($D01E)`; this clears **all** collision flags.

```asm
        lda M0PF              ; missile 0 vs PF0-PF3 pixels
        pha
        lda P0PF              ; player 0 vs PF0-PF3 pixels
        pha
        lda M0PL              ; missile 0 vs players
        pha
        lda P0PL              ; player 0 vs players
        pha
        lda #$00
        sta HITCLR            ; clear all collision latches
        pla
        sta collision_p0pl
        pla
        sta collision_m0pl
        pla
        sta collision_p0pf
        pla
        sta collision_m0pf
```
