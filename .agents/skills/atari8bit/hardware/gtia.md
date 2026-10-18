# GTIA Graphics Chip

Router for GTIA/CTIA registers, colour interpretation, player/missile graphics,
priority, and collisions.

Load only the focused file that matches the task.

- [overview.md](gtia/overview.md) - Quick lookup
- [registers-colors.md](gtia/registers-colors.md) - Register map at `$D000-$D01F`, shadows, colour/luminance model
- [gtia-modes.md](gtia/gtia-modes.md) - `PRIOR` bits 6-7 and GTIA 9/10/11 behaviour
- [player-missile.md](gtia/player-missile.md) - PMG memory, DMA/GRACTL enable, sizes, priority, and `VDELAY`
- [collisions.md](gtia/collisions.md) - Collision latches and `HITCLR`

For HIP/RIP/TIP and other scene-picture techniques built on top of GTIA modes,
also use `..\graphics\advanced-fx.md`.
