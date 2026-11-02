---
trigger: always_on
---

# Domain: Test Design & Asset Agnosticism

## 1. No Hardcoded Asset Counts or Dynamic Resource Metrics
- **Dynamic assets:** never hardcode expectations for content that evolves during development — screens and labyrinths in `world/project.yaml`, object definitions in `world/objects.yaml`, palettes in `world/colors.yaml`, frames in `sprites/jabberwocky.json`, animation/rotation entries in `chars/animated.json` / `chars/rotated.json`, lines in `texts/*.txt` (counts of objects, enemies, secrets, screens, levels, tiles, …).
- **Source of truth:** derive expected metrics dynamically from the source file inside the fixture/setup (parse it with the project's own loaders) instead of asserting integer constants such as `assert len(scene.objects) == 8`.
- **Behavioral assertions:** focus integration tests and py65 harnesses on engine logic, mechanics, state transitions and invariants (collision outcomes, energy decay, HSCROL phase order `3 → 2 → 1 → 0 → 3`, score updates, level advance) rather than brittle content snapshots.
- **Resource independence:** when a specific count is strictly required, use synthesized in-memory models or dedicated static fixtures inside `tests/` — never mutate or bind tests to live production assets.
- **Generated code is not a fixture:** do not assert against textual snapshots of `gen/*.asm`; test the generator's Python API/models and let the py65 harness validate the assembled behavior.

## 2. py65 Harness Contract (project convention)
- **Prerequisites:** a fresh build — `make test` depends on `jabberwocky.xex`, and the fixtures assert that both `jabberwocky.xex` and `gen/jabberwocky.lab` exist (run `make all` first).
- **Standard helpers** in each 6502 test module (see `tests/test_flame_collision.py` as the reference implementation):
  - `parse_labels()` — `.lab` file → `{SYMBOL: address}` mapping;
  - `load_xex()` — copy each XEX segment into a 64 KB `bytearray`;
  - `clean_mpu()` — `MPU(memory=mem)` over that buffer;
  - `run_subroutine()` — set `sp = 0xFD`, `stPushWord(0x0100 - 1)`, write `BRK` at `$0100`, set `pc` to the routine and step until `pc == 0x0100` with a bounded step budget.
- **Access memory through label addresses**, never through copied magic numbers, and assert on RAM/register state afterwards.
- **Test names** use plain `test_*` functions or `Test*` classes; each test must be independent of execution order.
- **Headless:** the suite runs on Windows without a window or an emulator process — GUI tests build their own `QApplication`.
