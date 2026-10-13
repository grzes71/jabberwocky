---
name: atari8bit-trackers
description: >-
  Atari music tracker integration for RMT and TMC2: player ABI, tick timing,
  feature files, relocators, stereo fallback, and interrupt coexistence.
---

# Music Trackers

## TMC2 Tracker Format

TMC2 and RMT are the two tracker ecosystems most often met on the Atari 8-bit; RMT (Raster Music Tracker) is the more widely used today, while TMC2 songs are still common in games from the 1990s. Treat either tracker as a black box: the exported player routine is the ABI, and both players occupy the POKEY audio registers for as long as they run.

A TMC2 module packs song data (order list, patterns, instrument definitions) into one binary blob that is replayed by its own player routine, entered once per music tick from the host's VBI or main loop.

### Playback Driver ISR

A TMC2 player is normally driven from the VBI deferred vector so that the host keeps the immediate vector for its own per-frame logic. Whichever vector your code hands the player, the handler must exit the way the OS expects for that slot:

```
VBI chain:  OS VBI
            ├── immediate vector VVBLKI ($0222)
            └── deferred vector VVBLKD ($0224)  <- player ISR
                    └── AUDC/AUDF shadow-to-hardware write burst
                        └── JMP XITVBV ($E462) -> OS resumes
```

A handler installed at the deferred vector (`VVBLKD`, `$0224`) returns with `JMP XITVBV` (`$E462`); a handler installed at `VVBLKI` (`$0222`) can return through the OS with `JMP SYSVBV` (`$E45F`). Note that a deferred handler runs with interrupts enabled and after the OS has done its screen and keyboard work, so keep the register writes short.

### Speed and Tempo

Players tick once per frame and use a frame counter to divide that rate down to the song's row rate, so the same song plays faster on NTSC (60 Hz) than on PAL (50 Hz). At a speed of 6 frames per row that is 10 Hz rows on NTSC but 8.33 Hz on PAL; tracker exports usually provide separate NTSC/PAL builds or a speed compensation, otherwise tempo and pitch-derived effects drift between systems.

### Key Data-Layout Rules

Do not decode module bytes by hand. The internal layout of a TMC2 or RMT module is owned by its player version; regenerate or re-export with the matching tracker/player instead of patching data by hand. What a host program needs to know is only:

- Where the module lives (a fixed address the player is initialised with).
- Which register/zero-page state the player owns and must be preserved.
- When to call play and when to call silence.

### Register Reuse Conventions

Tracker drivers normally update AUDFx/AUDCx in a tight burst once per music tick. When the song uses linked 16-bit channels or sample effects, the host must treat `AUDCTL`, `STIMER`, and channel ownership as part of the player ABI rather than freely reusing spare POKEY voices.

---

## RMT Tracker Format

RMT (Raster Music Tracker) is the most widely used Atari 8-bit tracker today. It exports a player written in assembly source plus a packed module, and it distinguishes between normal music channels and optional sound-effect channels selected by the player build. Treat the exported player entry points as the stable interface; do not infer channel layout from a module without checking the feature file or player configuration.

The exported files and their roles (see the RMT example shipped with MADS):

```
rmt_player.a65   — the player routine (included first)
< song >.feat    — feature flags for this song/player build
rmt_relocator.mac — macro that patches the module for relocation
< song >.rmt     — the packed module itself
```

Player entry points are fixed offsets from the `RASTERMUSICTRACKER` label:

```
jsr RASTERMUSICTRACKER     ; init: X/Y = module address, A = song line; returns instrument speed in A
jsr RASTERMUSICTRACKER+3   ; play one tick
jsr RASTERMUSICTRACKER+9   ; silence all channels
```

`STEREOMODE` in the feature file selects the build: `0` = mono 4 tracks, `1` = stereo 8 tracks, `2` = 4 tracks stereo L1 R2 R3 L4, `3` = 4 tracks stereo L1 L2 R3 R4.

### Tick Scheduling

RMT does not install any interrupt vector itself — the host calls `play` at the song's tick rate from a VBI, a VCOUNT-synchronised loop, or a raster routine. `init` returns the instrument speed (1–4) in `A`; RMT's own example lines in the player on instruments-per-screen timing by syncing to VCOUNT with a spacing table:

```asm
tabpp   dta 156,78,52,39    ; VCOUNT steps per play call for instrument speed 1..4
```

Because the tick is tied to the frame rate, an NTSC and a PAL machine play the same module at different tempos unless the player/module is built for the target system.

### Instrument Packing

Instrument packing and enabled effects depend on the generated RMT feature file. For agent-generated builds, include the module-specific feature file before the relocator/player macro and avoid hand-editing packed instrument tables unless the task is explicitly format-level tooling.

---

## Co-habitation Rules

| Question | TMC2 | RMT |
|----------|------|-----|
| Player delivery | binary blob containing its own player | player in source (`rmt_player.a65`) + packed module |
| Interrupt vector | player is driven from a vector or loop the host provides | player installs nothing; host calls `play` |
| Audio channels | 4 POKEY channels | 4 POKEY channels (stereo builds: 8 / 4-mixed) |
| Silence entry | player-specific stop/silence call | `jsr RASTERMUSICTRACKER+9` |
| Host controls tick | yes | yes (VCOUNT/VBI/raster) |

Both ecosystems consume the same POKEY registers, so:

- If the game owns DLI/VBI timing, call the player from inside that existing discipline instead of letting a demo example install vectors over yours.
- Treat `AUDCTL`, `STIMER` and the channel set the player updates as part of the player ABI; don't repurpose voices behind its back.
- Call the silence entry before returning to DOS or before loading another program.

## Practical RMT Relocator Patterns

Tracker relocator examples are useful because they show the whole build shape,
not just the player routine. The stable pattern is: include the player, include
or generate the module feature file, relocate module data to a fixed address,
then call init/play/silence through documented player entry offsets.

RMT demo pattern:

```asm
STEREOMODE = 0                  ; 0 = mono 4 tracks; 1 = stereo 8; 2/3 = 4 tracks stereo
        icl "..\rmt_player.a65"

MODUL = $1000
        org MODUL
        icl "music.feat"        ; feature flags generated for this song
        rmt_relocator 'music.rmt' MODUL

        org $3e00
start   ldx #<MODUL
        ldy #>MODUL
        lda #0                  ; song line
        jsr RASTERMUSICTRACKER  ; init

loop    jsr RASTERMUSICTRACKER+3 ; play once per frame or music tick
        jmp loop

stop    jsr RASTERMUSICTRACKER+9 ; silence
        run start
        icl '..\rmt_relocator.mac'
```

Rules for generated players:
- Place the RMT player on a page boundary (`PLAYER` low byte `$00`) and reserve its documented zero-page bytes.
- Include the `.feat` file before relocating module data; otherwise feature-optimized player branches will not match the module.
- Call `init` once with X/Y = module address and A = song line; call `play` from a stable VBI or VCOUNT-synchronized loop; call `silence` before returning to DOS.
- For stereo layouts, detect stereo POKEY first or provide a mono fallback.
- If a game owns DLI/VBI timing, wrap player calls inside the existing interrupt chain instead of letting a tracker example install vectors blindly.
