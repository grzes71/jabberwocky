# Project Context & Architecture — Jabberwocky (Atari 8-bit)

> **Note to Agent:** Basic 6502 hardware rules, Zero Page limits, syntax restrictions, memory boundaries and timing requirements are governed by `.agents/rules/` (see [02-asm-6502-rules.md](rules/02-asm-6502-rules.md)). This document defines the architecture, build pipeline and tooling specific to THIS project.

## 1. PROJECT ROLE & SCOPE

- You act as a Senior Embedded Systems Architect and Python Tooling Engineer.
- Primary focus: orchestrating the project — 6502 assembly (MADS) for engine/rendering/scene code plus Python (pydantic, PySide6, pytest, py65) for data compilation, desktop editors and tests.
- The repository also ships three PySide6 desktop tools (`labirynt_studio/`, `object_studio/`, `sprite_studio/`) and a CI release pipeline (`scripts/release_helper.py`, `.github/workflows/release.yml`); changes there follow the same SSOT and testing rules.
- Read context before touching an unfamiliar subsystem, in this order:
  1. `README.md` — feature overview, project tree, tool descriptions.
  2. `docs/memory_map.txt` (generated SSOT) — current segment layout and free headroom.
  3. `docs/architecture/memory_map_tool_spec.md` and the `docs/*plan*.md` / `docs/*walkthrough*.md` notes for the subsystem.
  4. The header comment of the file you are about to change.
- There is **no** `ARCHITECTURE.md` or `MEMORY_USAGE.md` in this repo — do not look for them.

---

## 2. DEVELOPMENT WORKFLOW (CRITICAL)

- **Verification sequence** — after modifying any file (`.asm`, Python, SSOT data, assets, rules) run **both**:
  ```bash
  make all      # assets + data -> jabberwocky.xex -> check_memory
  make test     # python -m pytest tests -v
  ```
  `make all` does **not** run pytest; tests are a separate target that depends on `jabberwocky.xex`. Never report a task as complete with a red `make all` or a red pytest run.

- **Target graph** (authoritative source: `Makefile`):

  | Target | What it does |
  | --- | --- |
  | `make` / `make all` | `jabberwocky.xex` + `check_memory` (no tests) |
  | `make assets` | `img/title.png` → `gen/title.bin` (ANTIC F, 320×175); `sprites/jabberwocky.json` → `gen/dragon_sprite.asm`; `texts/*.txt` → `gen/{intro,title_scroll,game_over_fail,game_over_success}_text.asm`; `music/music.sap` → `gen/music.cmc` (relocated to `$9000`) |
  | `make data` | `world/*.yaml` → `gen/world_data.asm` + `gen/world_obj_tiles.asm`; `chars/rotated.json` → `gen/rotated_chars_{global,proc}.asm`; `chars/animated.json` → `gen/animated_chars.asm` (charset base `$6800`) |
  | `make xex` | MADS assembly of `main.asm` → `jabberwocky.xex`, `gen/jabberwocky.lst`, `gen/jabberwocky.lab` |
  | `make check_memory` | `scripts/generate_memory_map.py` → `docs/memory_map.txt` + `.json` (non-zero exit on overlap) |
  | `make test` | full pytest suite (py65 harnesses + tools + GUI models) |
  | `make run` | Altirra 4.40 with the built `.xex` |
  | `make clean` | removes `jabberwocky.xex` and `gen/` |

- **Asset & code regeneration awareness:** every generated file is an explicit `Makefile` prerequisite. When adding a source or a generator, wire the dependency so the next `make` rebuilds it.
- **Generated artifacts are read-only:** never hand-edit `gen/*.asm`, `jabberwocky.xex`, `docs/memory_map.txt|json` — regenerate them via the owning script or target.
- **Error/warning resolution:** fix build errors, warnings and test failures before proposing further edits. If a test fails, determine whether it is pre-existing (compare against a clean build) before attributing it to your change — never mask or skip failures.
- **Test requirements:** unit and integration tests must pass before a task is complete; py65 harnesses verify that the Python data models and the assembled 6502 routines agree.

---

## 3. HIGH-LEVEL MEMORY ARCHITECTURE

1. **ROM banking (`PORTB` `$D301`)**
   - OS ROM stays enabled (`PORTB` bit 0 = 1) because the engine relies on OS VBLANK/`RTCLOK`; therefore `$C000`–`$CFFF` (OS kernel) and `$D000`–`$DFFF` (hardware registers) **MUST NEVER** be used as RAM.
   - BASIC ROM is disabled at load time by `disable_basic` (the `org INITAD` stub in `main.asm`, `PORTB` bit 1 = 1), which unlocks `$A000`–`$BFFF` for user data (CMC player, text VRAM). The `$BFFF` ceiling only holds while BASIC stays disabled.
   - All user code, graphics, data and tables end at or below `$BFFF`.

2. **Automated memory-map validation**
   - `scripts/generate_memory_map.py` (`make check_memory`) parses `gen/jabberwocky.lab`/`.lst`, writes `docs/memory_map.txt` + `.json`, and exits non-zero on segment overlap, a user symbol in Zero Page (`$00`–`$7F`), or usage above `$BFFF`.
   - The generated `docs/memory_map.txt` is the **single source of truth** for bounds and headroom — always re-read it after a change instead of trusting quoted numbers. Segments declared via `org` in the most recent build were: `$0800`–`$1EB1` ENGINE, `$2800`–`$3BF5` CODE, `$4000`–`$5B67` VRAM, `$5C00`–`$5FFF` FONT, `$6610`–`$6781` DLIST, `$6800`–`$86B0` FONT/world data, `$9000`–`$9921` music, `$9A00`–`$A155` CMC player, `$B000`–`$BEB4` text VRAM.
   - **Reserved at runtime but invisible to the checker** (equates only, no `org`): PMG `$2000`–`$27FF`, HSCROL action ring buffer `$6000`–`$641F` (11 rows × 96 B), status bar `$6420`–`$646F`. Treat them as occupied; never place a new segment in the "free" gaps the tool reports for `$1EB2`–`$27FF` or `$6000`–`$660F`.

3. **Audio memory isolation**
   - `engine/music.asm` defines `MUSIC_DATA_ADDR = $9000` and `CMC_PLAYER_ADDR = $9A00`; the `Makefile` relocates the SAP export with `scripts/extract_sap.py --target-address 0x9000`. Changing one without the other corrupts the build — update the equate, the script flag and the expectations together.
   - Keep player code and song data clear of the ring buffer, the display lists and the `$B000` text VRAM; no dynamic buffer may overlap the music block.

4. **Sequential assembly (`main.asm`)**
   - Top-level segments ascend: `$0800` (engine/low code) → `$2800` (main code) → `$4000` (VRAM) → `$5C00` (font) → `$6000` (ring buffer/status) → `$6610` (display lists) → `$6800` (game font + world data) → `$9000` (music) → `$9A00` (CMC player) → `$B000` (text VRAM).
   - The only sanctioned location-counter backtracking is the OS-vector stub pattern already used in `main.asm`: `org INITAD` … `org @end`, plus the trailing `org RUNAD`. Never emit the same range twice — XEX segments would overwrite each other at boot.

---

## 4. PROJECT STRUCTURE

| Path | Purpose |
| --- | --- |
| `main.asm` | Entry point: `INITAD`/`RUNAD` vectors, `disable_basic`, memory equates, display lists, state machine + main loop |
| `hardware.asm` | ANTIC/GTIA/POKEY/PIA/OS equates — the only place hardware addresses may be defined |
| `zeropage.asm` | Zero-page allocations: `$80`–`$89` used (`PTR_SRC`, `PTR_DST`, `ZP_TMP`, `PTR_BLK`, `PTR_COLL`), `$8A`–`$FF` free |
| `Makefile` | Build/verify/run targets (see §2) |
| `engine/` | `charset_anim.asm`, `sound.asm` (POKEY SFX), `music.asm` (CMC wrapper + song IDs), `cmc_player_reloc.asm`, `flame_collision.asm` (flame/dragon/secret collisions), `level_name.asm` |
| `scenes/` | `title.asm`, `intro.asm` (DLI), `game.asm` (physics, HSCROL ring buffer, screen streaming), `gameover.asm`, `top_scores.asm`, `text_utils.asm` |
| `world/` | **SSOT**: `project.yaml` (screens/labyrinths), `objects.yaml` (object catalog), `colors.yaml` (ANTIC 5 palettes) |
| `chars/` | **SSOT**: `animated.json` (tile animation frames), `rotated.json` (rotated tile variants) |
| `sprites/` | **SSOT**: `jabberwocky.json` (PMG sprite frames) |
| `texts/` | **SSOT**: `title.txt`, `scroll.txt`, `game_over_fail.txt`, `game_over_success.txt` |
| `fonts/` | `text.fnt` (Polish diacritics, at `$5C00`), `game.fnt` (playfield tiles, at `$6800`) |
| `img/`, `music/` | Source assets: `title.png` (→ ANTIC F), `music.sap` (→ CMC, relocated to `$9000`) |
| `gen/` | Generated ASM/binary — **never edit manually** |
| `scripts/` | `labirynt_builder.py`, `compile_sprites.py`, `compile_texts.py`, `convert_image.py`, `extract_sap.py`, `gen_animated_charset.py`, `gen_rotated_charset.py`, `generate_memory_map.py`, `release_helper.py` |
| `labirynt_studio/` | PySide6 screen/labyrinth editor → writes `world/project.yaml` |
| `object_studio/` | PySide6 object catalog editor → writes `world/objects.yaml` |
| `sprite_studio/` | PySide6 PMG sprite editor → writes `sprites/jabberwocky.json` |
| `tests/` | pytest suite: py65 harnesses, tool/model tests, GUI model tests |
| `docs/` | Generated `memory_map.txt`/`.json` + design notes/plans |
| `.github/workflows/release.yml` | Semantic-release pipeline driven by `scripts/release_helper.py` |
| `.agents/` | This file, `rules/`, `skills/` |

---

## 5. DATA PIPELINE & ASSET TOOLING

- **Single Source of Truth (SSOT):** editable sources live in `world/*.yaml`, `chars/*.json`, `sprites/*.json`, `texts/*.txt`, `fonts/*.fnt` and `music/*.sap`; Python tools compile them into `gen/`. Nothing else may be treated as hand-editable source.
- **Generator map:**

  | Generator | Source | Output |
  | --- | --- | --- |
  | `scripts/labirynt_builder.py` | `world/project.yaml`, `world/objects.yaml`, `world/colors.yaml` | `gen/world_data.asm`, `gen/world_obj_tiles.asm` |
  | `scripts/compile_sprites.py` | `sprites/jabberwocky.json` | `gen/dragon_sprite.asm` |
  | `scripts/compile_texts.py` | `texts/*.txt` | `gen/intro_text.asm`, `gen/title_scroll_text.asm`, `gen/game_over_fail_text.asm`, `gen/game_over_success_text.asm` |
  | `scripts/convert_image.py` | `img/title.png` | `gen/title.bin` |
  | `scripts/extract_sap.py` | `music/music.sap` | `gen/music.cmc` (target `$9000`) |
  | `scripts/gen_animated_charset.py` | `chars/animated.json` | `gen/animated_chars.asm` |
  | `scripts/gen_rotated_charset.py` | `chars/rotated.json` | `gen/rotated_chars_global.asm`, `gen/rotated_chars_proc.asm` |

- **Structure-of-Arrays (SoA):** multi-attribute data is emitted as parallel tables (`screens_coords_lo/hi`, `screens_codes_lo/hi`, …) so 6502 code indexes with `LDA table,X`. Never emit AoS records for engine tables.
- **Build-time validation:** validate coordinates, collision flags, destroyed masks and pointer links in Python (pydantic models, `labirynt_studio/validation`) before writing ASM — a bad source must break `make data`, not the game.
- **Editors write the SSOT:** `labirynt_studio` → `world/project.yaml`, `object_studio` → `world/objects.yaml`, `sprite_studio` → `sprites/jabberwocky.json`. Re-run `make all` after every editor save; manual SSOT edits require explicit user approval (see `rules/01-global-rules.md`).

---

## 6. ENGINE ARCHITECTURE & FRAME PIPELINE

- **Deterministic main loop** (`main.asm`, one iteration per `RTCLOK+2` tick — 50 Hz PAL / 60 Hz NTSC):
  1. Wait for the next vertical-blank tick (poll `RTCLOK+2`).
  2. `Audio_Update` — POKEY SFX state machine + CMC music tick.
  3. `update_input` — joystick/`STRIG0` read with falling-edge `fire_pressed`.
  4. `dispatch_state` — on a state change run `*_init`, otherwise `*_run` (`scene_init_tbl` / `scene_run_tbl`).
  5. Inside `*_run`: dragon physics (8.8 fixed point), flame animation, object and secret collisions, deferred screen baking.
- **Deferred baking:** coarse-scroll frames only shift the HSCROL ring buffer; new columns/tiles are baked later from `bake_pending` through `execute_pending_bake`, keeping scroll frames stable at 50/60 FPS.
- **Decoupled module communication (mailbox pattern):** modules talk through globals/flags — one module raises a request (`bake_pending`, `fire_state`, `dragon_hit_pending`, …), the owning module consumes and clears it in its scheduled phase. O(1), no deep call chains.
- **Interrupts (as actually implemented):**
  - No custom NMI handler: the engine keeps the OS VBLANK and synchronises by polling `RTCLOK`.
  - `intro.asm` installs a deferred VBLANK vector (`SETVBV` type 7) and a DLI vector (`VDSLST`) for per-text-line colour fades; `game.asm`, `title.asm` and `level_name.asm` disable NMI via `NMIEN` (`$D40E`) where DLIs are not wanted.
  - DLI routines stay short, save/restore A/X/Y and touch only hardware registers (`COLOR*`/`COLPF*`, `CHBASE`, `HPOSP*`).
- **Display hardware:** ANTIC 5 action playfield (11 lines × 48 B, `HSCROL` `$D404`, per-row `LMS` mirror ring buffer), ANTIC 2 status bar, ANTIC F title bitmap, PMG players/missiles at `$2000`–`$27FF` with the 5th-player flame (`GPRIOR`, `COLPF3`).

---

## 7. PYTHON & TESTING STANDARDS

- **Stack** (pinned in `requirements.txt`): Python 3.10+, `pydantic` 2.x, `PyYAML`, `PySide6` 6.11, `pytest` 9.x, `py65` 1.2, `Pillow`, `numpy`, `atari-image-converter` (wheel). Keep the file minimal — justify any addition.
- **Python tooling:** full type hints, `from __future__ import annotations`, `dataclasses` or pydantic v2 models, `argparse` CLIs (this project does not use `click`) with `0`/non-zero exit codes wired into `make`. Every generated ASM file starts with an `; AUTO-GENERATED … — do not edit` header.
- **GUI code** lives in `labirynt_studio/`, `object_studio/`, `sprite_studio/`; tests build their own `QApplication` (no `pytest-qt` dependency) and must run without a visible window.
- **py65 integration-test pattern** (reference implementation: `tests/test_flame_collision.py`):
  1. Use the already-built `jabberwocky.xex` + `gen/jabberwocky.lab` — tests never invoke MADS; `make test` depends on `xex`.
  2. `parse_labels()` turns the `.lab` file into `{SYMBOL: address}`.
  3. `load_xex()` copies each XEX segment into a 64 KB `bytearray`; `MPU(memory=mem)` wraps it.
  4. Seed registers/RAM via label addresses, set `sp = 0xFD`, `stPushWord(0x0100 - 1)`, place `BRK` at `$0100`, set `pc` to the routine and step until `pc == 0x0100` with a bounded step budget.
  5. Assert RAM/state invariants — never asset counts (see `rules/05-tests.md`).

---

## 8. AVAILABLE AGENT SKILLS

Consult these before improvising; they are the authoritative references for their domains:

| Skill | Path | Description & Trigger Criteria |
| --- | --- | --- |
| `atari-image-converter` | `.agents/skills/atari-image-converter/SKILL.md` | Modern image → ANTIC bitmap/graphics conversion (drives `scripts/convert_image.py`, `img/title.png` → `gen/title.bin`). |
| `atari-music-composer` | `.agents/skills/atari-music-composer/SKILL.md` | POKEY music tooling and the SAP/CMC pipeline (`music/music.sap` → `gen/music.cmc`). |
| `atari8bit` | `.agents/skills/atari8bit/SKILL.md` | Atari XL/XE hardware/OS reference router (ANTIC, GTIA, POKEY, PMG, display lists, interrupts). |
| `mads` | `.agents/skills/mads/SKILL.md` | MADS assembler: directives, pseudo-commands, labels, macros, procedures, banks. |
| `altirra-bridge` | `.agents/skills/altirra-bridge/SKILL.md` | Scripting AltirraSDL over the bridge: boot XEX, frame-step, registers/memory, screenshots, input injection (see `rules/06-altirra-sdl-rules.md`). |
| `py65` | `.agents/skills/py65/SKILL.md` | Writing pytest 6502 harnesses with `py65` (`MPU`, `.lab` labels, memory assertions). |
| `done` | `.agents/skills/done/SKILL.md` | Task wrap-up: prepend the `HISTORY.md` entry exactly as `rules/04-history-rules.md` requires. |
| `git-push` | `.agents/skills/git-push/SKILL.md` | Branch/stage/commit (Conventional Commits, English) and push to `origin`. |

> `done` and `git-push` replaced the former `.agents/workflows/*.md` files — use the skill paths above.
