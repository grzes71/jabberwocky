---
name: atari-music-composer
description: >-
  Use for Atari Music Composer tooling and POKEY audio pipelines: composing
  music procedurally or with AI, validating 4-channel POKEY constraints,
  parsing and compiling Music DSL and AICompositionDoc, rendering audio to WAV,
  or exporting relocatable 6502 assembly (player.asm) and MADS data.
---

# Atari Music Composer — AI Agent Skill & Tooling Reference

## 1. Overview & Core Purpose

`atari-music-composer` is an embedded audio tooling system and compositional pipeline designed for **Atari 8-bit computers (Atari 800 XL / 65 XE)** equipped with the **POKEY sound chip** and running on the **MOS 6502** microprocessor.

### Problems Solved
1. **POKEY Hardware Complexity:** Translates high-level musical ideas into accurate 64 kHz / 15 kHz frequency dividers (`AUDF1..4`), polynomial distortion modes (`AUDC1..4`), ADSR envelope ticks, and paired 16-bit pure tone bass registers without requiring manual calculation of divider tables.
2. **Strict Hardware Monophony & Resource Budgets:** POKEY features exactly 4 monophonic hardware audio channels and severe memory limits. The engine enforces monophony, validates 4-voice allocations, and guarantees compact Structure-of-Arrays (SoA) byte streams fitting within standard Atari RAM limits ($< 2$ KB total footprint).
3. **Bridging AI to 6502 Assembly:** AI models cannot reliably generate raw 6502 machine code or glitch-free hardware register writes directly. This toolkit establishes a declarative intermediate representation (`AICompositionDoc` v1) with a deterministic 3-tier validation engine and an automated Composition Repair Loop.
4. **Relocatable Game Engine Integration:** Provides a standalone, clean 6502 player (`player.asm`) that consumes under $1.5$ KB RAM, requires only 10 Zero Page bytes, takes $\sim 110\text{--}140$ CPU cycles per frame ($< 1.5\%$ of a 50 Hz PAL frame), and installs at any memory address without code changes.

---

## 2. Capabilities Matrix

| Capability | Status | CLI Command / Python API | AI Required | External Binary Required | Primary Output |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Procedural Composer v4** | Production | `atari-music compose` / `generate_music()` | No | None | `MusicGenerationResult` (IR, WAV, ASM, JSON) |
| **POKEY Software Synth** | Production | `--output-wav` / `render_pokey_to_wav()` | No | None | 44.1 kHz 16-bit mono PCM `.wav` |
| **MADS ASM Exporter** | Production | `atari-music export-mads` / `export_mads_asm()` | No | None | Relocatable MADS assembly `.asm` |
| **6502 Relocatable Player** | Production | `player.asm` (included in root) | No | MADS (for assembly) | 6502 object code / `.xex` |
| **Standalone XEX Builder** | Production | `atari-music build-xex` / `build_xex_from_composition()` | No | `tools/mads/mads.exe` or `mads` in PATH | Standalone bootable Atari `.xex` |
| **AI Composition (OpenAI/DeepSeek)** | Production | `atari-music ai-compose` / `request_ai_composition()` | **Yes** | None (requires network / API key) | `AICompositionDoc` JSON or Music DSL |
| **Music DSL Parser & Serializer** | Production | `atari-music import-dsl` / `parse_music_dsl()`, `export_music_dsl()` | No | None | Validated `AICompositionDoc` / `.dsl` text |
| **Mock AI Composition** | Production | `atari-music ai-compose --provider mock` | No | None | Deterministic `AICompositionDoc` / DSL |
| **3-Tier Music Validator** | Production | `atari-music import-json`, `import-dsl` / `validate_composition()` | No | None | `ValidationReport` & validated doc |
| **Composition Repair Loop** | Production | `generate_composition_with_retry()` | If using AI | None | Self-corrected `AICompositionDoc` |
| **Musical Property Analysis** | Production | `atari-music analyze` / `analyze_composition()` | No | None | Rhythm/Melody/Harmony metrics + SHA-256 |
| **Macro-Structure & Form Analysis** | Production | `atari-music analyze --structure` / `analyze_composition_structure()` | No | None | `DetailedStructureMetrics` (repetition, form) |
| **Dataset Extraction from SAP** | Historical/Tool | `atari-music extract` | No | `tools/asap/asapscan.exe` (local only) | `dataset.jsonl`, `.dump.gz` files |
| **Ground-Truth Duration Check** | Production | `calculate_composition_duration()` | No | None | Precise playback seconds @ 50 Hz PAL |

> **Note on Local Binaries:** The Python synthesizer, POKEY IR compiler, MADS code exporter, validator, and structural analyzer are 100% self-contained in pure Python with zero external binary dependencies. Only assembling into `.xex` binaries requires MADS (`mads.exe`).

---

## 3. When to Use This Skill

Use this skill when:
- An Atari 8-bit game or demo needs background music, title themes, or jingles.
- A project requires generating POKEY-compatible music either **procedurally** (deterministic non-AI) or via an **LLM** (AI-directed).
- High-level musical descriptions (tempo, key, mood, patterns, form) need to be converted into **MOS 6502 / MADS assembly**.
- An existing Atari 6502 assembly project needs to integrate a **relocatable 4-channel audio driver**.
- AI-generated music needs to be **validated against physical POKEY constraints** (strict monophony per channel, 16-bit bass channel coupling, 4-bit volume limits).
- A composition needs to be evaluated for **macro-structural variety, repetition ratio, or thematic variation**.
- Music needs to be previewed as standard **WAV audio** on modern systems without booting an emulator.

---

## 4. Full Pipeline Architecture

```text
               USER INTENT / SPECIFICATION
                           │
         ┌─────────────────┴─────────────────────────────┐
         ▼                                               ▼
 [Procedural Path: Non-AI]                   [Generative Path: AI LLM]
  Composer v4 Engine (Python)                 OpenAI / DeepSeek Provider
  - 6 Canonical Profiles                      - JSON or Music DSL (--format)
  - Algorithmic Counterpoint                  - Form Planning & Variations
  - Bass & Percussion Engines                    │                     │
         │                                       │ JSON                │ Music DSL
         │                                       ▼                     ▼
         │                               ┌──────────────┐      ┌──────────────┐
         │                               │AIComposition │      │  DSL Parser  │
         │                               │     Doc      │◄─────┤  (lossless)  │
         │                               └───────┬──────┘      └──────────────┘
         │                                       │
         │                                       ▼
         │                               3-Tier Validation Engine
         │                               - Tier 1: Schema
         │                               - Tier 2: Musical Grammar
         │                               - Tier 3: Hardware Monophony
         │                                          │
         │                        [Failure] ────────┴──────── [Valid]
         │                            │                          │
         │                            ▼                          │
         │                   Composition Repair Loop             │
         │                   - Formatted Error Feedback          │
         │                   - Re-prompt Model (max 2-3 retries) │
         │                            │                          │
         │                            └───────────┬──────────────┘
         │                                        ▼
         └─────────────────┬──────────────────────┘
                           │
                           ▼
                  Symbolic Music IR (MusicSong)
                  - Monophonic tracks (Lead, Harmony, Bass, Perc)
                  - Named pitches (e.g. C4, D#2), step durations
                           │
                           ▼
                  POKEY IR (IRSong)
                  - AUDF frequency dividers (64 kHz / 15 kHz / 1.79 MHz)
                  - AUDC distortion bytes ($A0 pure, $C0 poly, $00 noise)
                  - 4-channel instrument ADSR envelopes
                  - Speed divisor (frames_per_tick @ 50 Hz PAL)
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
 [Software Synthesis]                 [MADS 6502 Exporter]
  pokey_synth.py                       mads_exporter.py
  - Emulated POKEY registers           - Structure-of-Arrays (SoA)
  - 44.1 kHz 16-bit mono WAV           - Compact RLE byte streams
  - Volume normalization               - music_data.asm (< 750 B)
         │                                   │
         ▼                                   ▼
   Audio Preview (.wav)               MADS Assembler (tools/mads)
                                       - Links player.asm + music_data.asm
                                       - Configures Zero Page ($80..$F0)
                                       - Sets memory origin ($4000..$A000)
                                             │
                                             ▼
                                     Atari XEX Executable (.xex)
                                     - Interactive ANTIC Mode 2 UI
                                     - Real-time MM:SS timer & VU meters
                                     - Key mute toggle ($02FC)
```

---

## 5. Non-AI Mode vs. AI Mode

### A. Non-AI Mode (Procedural / Deterministic)
In Non-AI mode, music is synthesized algorithmically via **Composer v4** without network access or LLM inference.
- **Profiles:**
  - `title`: Hymnic, melodic lead, structured 4-channel harmony.
  - `exploration`: Slower tempo, modal scales (Dorian/Mixolydian), breathing textures.
  - `action`: Fast tempo (130--170 BPM), syncopated driving bass, 16th-note percussion groove.
  - `funny`: Bouncy, staccato articulations, sudden pitch leaps, humorous accents.
  - `dungeon`: Dark, low registers, ostinato lines, **16-bit pure tone bass coupling** on Channels 1+2.
  - `ending`: Resonant major/modal chordal voicings, march-style cadences.
- **Controls:** Seed (`--seed`), root key (`--key`), tempo (`--tempo`), intensity (`--intensity`), motivic variation level (`--variation`), length (`--length` short/medium/long).
- **Execution:** Zero external dependencies, deterministic outputs, instant generation ($< 0.1\text{ s}$).

### B. AI Mode (LLM Directed)
In AI mode, an LLM acts strictly as a **symbolic composer and arranger**. The model does **NOT** generate 6502 opcodes or direct hardware register values.
- **Model Role:** Generates a structured composition in either **canonical JSON** (`AICompositionDoc`) or compact **Music DSL** (`.dsl`).
- **Input Formats (`--format`):**
  - `json` (default): Schema-constrained JSON representation.
  - `dsl`: Ultra-compact, line-oriented Music DSL (~49.4% token reduction in empirical benchmarks), parsed directly and losslessly into `AICompositionDoc`.
- **Providers:**
  - `openai`: Connects to DeepSeek (`api.deepseek.com`) or OpenAI endpoints using standard API keys and Structured Outputs (`beta.chat.completions.parse` or JSON object fallback).
  - `mock`: Offline deterministic mock provider supporting canned success and repair scenarios.
- **Arrangement Features:**
  - `form_plan`: High-level architectural plan (e.g. `rondo_variation`, `ternary_variation`).
  - `role`: Pattern classification (`intro`, `theme`, `variation`, `contrast`, `bridge`, `breakdown`, `fill`, `outro`).
  - `variation_of`: Explicit thematic derivation linking variation patterns to base themes.
  - `texture_notes`: Dynamic instrumentation shifts (e.g. "bass and drums breakdown").

---

## 6. Composition Data Model (`AICompositionDoc` v1)

All AI and import workflows operate on the versioned `atari-music-composition` schema defined in `src/atari_music/ai/schema.py` (serving as the Single Source of Truth, regardless of whether input was JSON or Music DSL):

```json
{
  "format": "atari-music-composition",
  "version": 1,
  "metadata": {
    "title": "Dungeon Depths",
    "author": "AI Composer",
    "key": "A",
    "mode": "dorian",
    "bpm": 90,
    "duration_seconds": 64.0
  },
  "hardware": {
    "channels": 4,
    "use_16bit_bass": true
  },
  "instruments": [
    {
      "id": "lead",
      "name": "Square Lead",
      "character": "bright_lead",
      "attack_frames": 1,
      "decay_frames": 4,
      "sustain_vol": 12,
      "release_frames": 6
    },
    {
      "id": "deep_bass",
      "name": "16-bit Sub Bass",
      "character": "bass"
    },
    {
      "id": "perc",
      "name": "Noise Snare",
      "character": "percussion"
    }
  ],
  "patterns": [
    {
      "id": "ThemeA",
      "length_steps": 16,
      "role": "theme",
      "channels": {
        "1": [
          {"step": 0, "note": "A3", "instrument": "lead", "duration": 4, "volume": 14},
          {"step": 4, "note": "C4", "instrument": "lead", "duration": 4, "volume": 14},
          {"step": 8, "note": "E4", "instrument": "lead", "duration": 8, "volume": 12}
        ],
        "2": [],
        "3": [
          {"step": 0, "note": "A1", "instrument": "deep_bass", "duration": 16, "volume": 14}
        ],
        "4": [
          {"step": 4, "note": "C5", "instrument": "perc", "duration": 2, "volume": 10},
          {"step": 12, "note": "C5", "instrument": "perc", "duration": 2, "volume": 10}
        ]
      }
    },
    {
      "id": "ThemeA_var",
      "length_steps": 16,
      "role": "variation",
      "variation_of": "ThemeA",
      "channels": { ... }
    }
  ],
  "sequence": ["ThemeA", "ThemeA_var", "ThemeA"],
  "loop_point": 0
}
```

### Key Schema Elements:
1. **`patterns` & `channels`:** Channel keys can be 1-based (`"1".."4"`) or 0-based (`"0".."3"`). The engine normalizes them to 1..4.
2. **`events`:** Each event must specify `step` (0-indexed offset within pattern), `note` (standard pitch name e.g. `"A3"`, `"F#2"`, or rest `"---"`/`"REST"`), `instrument` (matching an ID in `instruments`), `duration` ($\ge 1$), and `volume` ($0..15$).
3. **Monophony Constraint:** Overlapping notes on the same channel within a pattern are strictly illegal (`step + duration > next_step`).
4. **`sequence` & `loop_point`:** The playback order is an array of pattern IDs. `loop_point` defines the zero-based index in `sequence` to jump back to when the end is reached.
5. **16-Bit Bass Coupling (`use_16bit_bass: true`):** Hardware Channels 1 and 2 are joined (`AUDCTL = $10`). Channel 1 holds the combined 16-bit frequency divider, while Channel 2 is a hardware slave and must have **no independent active notes**.

---

## 7. 3-Tier Validation & Composition Repair Loop

Every composition passes through the 3-Tier Validator (`src/atari_music/ai/validation.py`):

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Schema Validation (MusicCompositionSchemaError)                │
│ - JSON structure, required fields, format == "atari-music-composition" │
│ - Version == 1, valid types, ranges (BPM 40..250, channels 1..4)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ PASS
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 2: Musical Validation (MusicCompositionValidationError)           │
│ - Strict channel monophony (NOTE_OVERLAP check)                        │
│ - Valid note strings, pitch bounds (playable POKEY frequencies)        │
│ - Pattern duration bounds: step + duration <= length_steps             │
│ - Reference integrity: instrument IDs exist, pattern IDs in sequence   │
│ - Sequence validity: non-empty, loop_point in range                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ PASS
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 3: Hardware Validation (MusicIRValidationError)                   │
│ - Max 4 simultaneous POKEY channels                                    │
│ - 16-bit bass pairing conflicts (BASS16_CHANNEL_CONFLICT on Ch1+Ch2)    │
│ - 4-bit volume range (0..15)                                           │
│ - Distortion modes ($A0 pure, $C0 4-bit poly, $00 5-bit poly noise)    │
└────────────────────────────────────────────────────────────────────────┘
```

### The Composition Repair Loop
When an AI provider generates a document with errors:
1. Validator generates a structured `ValidationReport` accumulating all issues with exact paths (e.g. `patterns[ThemeA].channels[1].events[2]`).
2. `ValidationReport.format_feedback()` generates a precise markdown correction prompt containing error codes (`NOTE_OVERLAP`, `INVALID_NOTE`), locations, and an explicit preservation directive: *"Preserve all valid parts of the existing composition. Modify ONLY what is necessary to resolve the reported validation errors."*
3. The client calls the provider again with the invalid composition and feedback (up to `max_retries`, default: 3).

---

## 8. Output Artifacts Deep Dive

### A. Music Data (`music_data.asm`)
Generated by `export_mads_asm()`. Formatted as Structure-of-Arrays (SoA) for $O(1)$ 6502 indexed addressing:
- **Header (6 bytes):**
  - `frames_per_tick` (.byte): VBLANK tick divider (e.g. 3..6 frames per step @ 50 Hz).
  - `audctl_mode` (.byte): POKEY `AUDCTL` register configuration (`$00` for 8-bit, `$10` or `$50` for 16-bit bass).
  - `instruments_ptr` (.word): Pointer to 20-byte instrument table.
  - `sequence_ptr` (.word): Pointer to sequence word list.
- **Instrument Table (20 bytes):** 4 channels $\times$ 5 bytes: `distortion`, `attack_frames`, `decay_frames`, `sustain_vol`, `release_frames`.
- **Sequence Table:** List of words pointing to pattern track descriptors, terminated by `$FFFF`.
- **Pattern Track Lists:** 4 words per pattern pointing to `ch1_data`, `ch2_data`, `ch3_data`, `ch4_data`.
- **Track Event Streams:** Compact 3-byte events: `.byte audf, duration_ticks, volume`. Terminated by `.byte $FF`.

### B. Relocatable 6502 Player (`player.asm`)
The player code in the root directory is written in official MOS 6502 assembly (MADS syntax) and has **zero hardcoded memory addresses**.

#### Public API:
```asm
music_init        ; Inputs: X = song_data low byte, Y = song_data high byte
                  ; Initializes song pointers, resets envelopes, silences POKEY.
music_play        ; Starts or unpauses playback.
music_stop        ; Stops playback and silences all 4 POKEY audio channels.
music_update      ; Advances sequencer and volume envelopes.
                  ; MUST be called exactly once per 50 Hz VBLANK frame.
music_is_playing  ; Returns A=1 if playing, A=0 if stopped/paused.
```

#### Zero Page Requirements:
Requires exactly 10 bytes in Zero Page. Default base is `$80` (`$80..$89`).
To relocate to another Zero Page area in your project:
```asm
PLAYER_ZP_BASE = $90    ; Relocate player Zero Page pointers to $90..$99
icl 'player.asm'
```

#### Memory Budget:
- Player code: **754 bytes**
- Player RAM variables: **55 bytes**
- Music data: **340--750 bytes** (depending on song length)
- Total RAM consumption: **$< 1.6$ KB**

#### The one hard limit: the player must be strictly smaller than 2048 bytes
The project's only byte limit applies to the **assembled player** (code + runtime state), and it is
**exclusive** — a player of exactly 2048 bytes fails. Measured through
`atari_music.stage15.measure_player_size` (MADS on an `org $6000` wrapper, `-b:$6000 -o:...bin`),
the player currently assembles to **1016 bytes**.

Three other quantities are *not* bounded by it, and must not be conflated with it:

| quantity | bounded by 2048? |
| :--- | :--- |
| assembled player (code + runtime state) | **yes — strictly below** |
| exported song data (patterns, sequence, instrument table) | no — separate, much smaller POKEY-IR budget |
| complete `.xex` file (harness + player + song data) | **no — not bounded at all** |
| loaded segments (`org` addresses and lengths) | no — bounded by the Atari memory map |

Ask `atari_music.stage15.player_size_limit_ok(size)` / `check_player_size(size)` rather than
comparing against 2048 directly; `reports/stage15/player_size_analysis.json` is the authoritative
record.

#### XEX memory layout is validated, not the file size
Because the file's size is not a criterion, `build-xex` parses the container MADS emitted
(`atari_music.xex_layout`) and judges the **address ranges**:

- user segments must lie entirely inside `$0400-$BFFF` — below is zero page, the hardware
  stack and the OS/DOS vectors this binary itself uses (RUN `$02E0/$02E1`, IOCBs `$0340-$03BF`,
  the `$02C6`/`$02C8`/`$02FC` shadows, the player's zero page); above is OS kernel ROM
  (`$C000-$CFFF`), hardware registers (`$D000-$DFFF`, including POKEY) and OS ROM
  (`$E000-$FFFF`). `AGENTS.md` §3.1: user code and data must end at or below `$BFFF`;
- `$A000-$BFFF` (the BASIC ROM window) is permitted on purpose — the project relocates there;
- two segments may never claim the same memory (the loader writes them in file order);
- the RUN/INIT vector blocks are loader protocol and are exempt.

A failure removes the binary just written and names the segment, its range and the reason. See
[docs/xex_memory_layout.md](docs/xex_memory_layout.md).

---

## 9. CLI Reference

The CLI entrypoint is `atari-music` (or `python -m atari_music`).

### Global Option: `--log-level`
Accepts `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (case-insensitive).
- **Default:** `WARNING` (ensures zero console clutter; stdout is clean for data pipelines).
- **Stream:** Logs are directed to `sys.stderr`.
- **Secret Redaction:** API keys (`sk-...`) and Authorization headers are automatically redacted in all log messages.

```bash
# Global options before subcommand:
atari-music --log-level DEBUG compose --profile action -o test.wav
atari-music --env-file custom.env ai-compose --style "dungeon" -o dungeon.json

# Or as options directly on ai-compose:
atari-music ai-compose --env-file custom.env --provider openai --log-level DEBUG --style "dungeon" -o dungeon.json
```

### Core Commands

#### 1. `compose` (Procedural Non-AI Generator)
```bash
atari-music compose \
    --profile action \
    --seed 301 \
    --key G \
    --tempo 140 \
    --length medium \
    --intensity 0.8 \
    --variation 0.5 \
    --output-wav action.wav \
    --output-json action.json \
    --output-asm action_data.asm
```

#### 2. `ai-compose` (LLM Composition Generator)
```bash
# Generate canonical JSON composition:
atari-music ai-compose \
    --style "dark dungeon exploration" \
    --mood mysterious --mood tense \
    --duration 75.0 \
    --bpm 88 \
    --channels 4 \
    --use-16bit-bass \
    --provider openai \
    --model deepseek-flash \
    --format json \
    --max-retries 3 \
    --output dungeon.json

# Generate compact Music DSL composition (--format dsl):
atari-music ai-compose \
    --style "dark dungeon exploration" \
    --format dsl \
    --output dungeon.dsl
```

#### 3. `import-json` (Validate, Render & Export Composition JSON)
```bash
atari-music import-json dungeon.json \
    --output-wav dungeon.wav \
    --output-asm dungeon_data.asm \
    --output-ir dungeon_pokey.json
```

#### 4. `import-dsl` (Validate, Render & Export Music DSL)
```bash
atari-music import-dsl dungeon.dsl \
    --output-wav dungeon.wav \
    --output-asm dungeon_data.asm \
    --output-ir dungeon_pokey.json \
    --output-json canonical_dungeon.json
```

#### 5. `export-mads` (Convert POKEY IR JSON to MADS ASM)
```bash
atari-music export-mads dungeon_pokey.json -o dungeon_data.asm
```

#### 6. `build-xex` (Directly Compile Composition JSON or DSL to Atari XEX)
```bash
# From JSON:
atari-music build-xex dungeon.json \
    --format json \
    --output dungeon.xex \
    --player-address 0x4000 \
    --music-address 0x6000 \
    --zp-base 0x80 \
    --player-asm player.asm \
    --mads tools/mads/mads.exe

# From Music DSL:
atari-music build-xex dungeon.dsl \
    --format dsl \
    --output dungeon.xex \
    --player-address 0x4000 \
    --zp-base 0x80
```
> Note: `player.asm` is resolved automatically by checking (1) current working directory, (2) repository root, and (3) packaged asm directory, or can be specified explicitly via `--player-asm`.


#### 7. `analyze` (Analyze Musical & Hardware Properties of Composition JSON)
```bash
# Human-readable terminal report (rhythm, melody, harmony, POKEY hardware, SHA-256 fingerprint):
atari-music analyze dungeon.json

# Include macro-structural form analysis (deduced form, repetition, diversity):
atari-music analyze dungeon.json --structure

# Machine-readable JSON output for automated agent pipelines:
atari-music analyze dungeon.json --json
atari-music analyze dungeon.json --structure -o analysis.json
```


---

## 10. Debugging, Logging & Stream Separation

### Architectural Rule: Strict Separation of Logs and Composition Data

`atari-music-composer` maintains a strict architectural boundary between diagnostic logging and composition output data:

1. **Python `logging` Exclusively for Diagnostics:** All application diagnostics, network telemetry, and validation notices use Python's standard `logging` framework (or CLI informational echoes directed to `stderr`).
2. **`stderr` for Diagnostics, Never `stdout`:** All log records and diagnostic messages are emitted strictly to `stderr`. They **must never** contaminate `stdout`.
3. **Clean, Parseable `stdout`:** When `stdout` is used for machine-readable output (such as piping `ai-compose` output), it contains **only** the requested data/result (valid JSON) and remains cleanly parseable by tools (`jq`, Python `json.loads`) independently of the active `--log-level` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
4. **Composition Artifacts Separated from Logs:** Composition data and generated artifacts (`.json`, `.asm`, `.wav`, `.xex`) are completely decoupled from diagnostic logs. Output files written to disk contain pure artifact data without log banners.
5. **No Semantic Changes under `--log-level DEBUG`:** Enabling `--log-level DEBUG` increases the volume of diagnostic information sent to `stderr` but **never** alters the semantic content, structure, or formatting of composition outputs on `stdout` or in files.
6. **Dual-Stream Contract for Agent Integration:** Agents integrating this tool into automated pipelines or external subagents must treat diagnostic logs (`stderr`) and composition artifacts (`stdout` or generated files) as two separate, independent data streams.
7. **Diagnostic Only (No LLM Log Scraping):** Debug logging of LLM/API requests and responses (payloads, token stats, timings) is strictly for diagnostics; it **must never** be relied upon or parsed as an output interface. Always use the structured composition JSON.
8. **Universal Secret Redaction:** Secret masking and redaction apply at all times to diagnostic logging. Even under `--log-level DEBUG`, API keys, Bearer tokens, and sensitive headers are guaranteed to be redacted before emission to `stderr`.

#### Practical Piping Example

Redirect machine-readable composition JSON from `stdout` while diagnostic logs stream cleanly to `stderr`:

```bash
# Diagnostic logs (API payload, validation results, repair attempts) go to stderr.
# Clean, validated JSON composition goes to stdout -> composition.json.
atari-music --log-level DEBUG ai-compose \
    --style "dark dungeon exploration" \
    --duration 45.0 \
    --provider openai \
    --model deepseek-flash > composition.json

# composition.json is 100% valid JSON and immediately parseable:
jq .format composition.json
# Output: "atari-music-composition"
```

### What is logged in `DEBUG`:
1. **API Endpoint & Parameters:** Target base URL (sanitized), model name, message count, message roles, and temperature.
2. **Payload:** The complete JSON payload sent to the LLM.
3. **API Response:** Received HTTP response ID, approximate character size, and latency.
4. **Structured Parsing:** Indicates whether native structured parsing (`beta.chat.completions.parse`) succeeded or if JSON object fallback parsing was invoked.
5. **Validation Diagnostics:** Full list of validation issues found by category, machine-readable code, and exact JSON path.
6. **Repair Loop Trace:** Attempt index, feedback text transmitted to the model, and resolution status.
7. **Credentials Safety:** Any string matching API keys (`sk-...`) or Bearer tokens is masked to `sk-x...xxxx` or `[REDACTED]` prior to emission.

---

## 11. Typical Workflows

### Workflow A: Generate Procedural Music (Non-AI)
```bash
# Generate action music in G minor at 145 BPM, export both audio preview and 6502 assembly:
atari-music compose --profile action --seed 1234 --key G --tempo 145 --output-wav action.wav --output-asm action_data.asm
```

### Workflow B: Generate and Validate Music with AI (LLM)
```bash
# Configure environment (.env or environment variable):
export AI_API_KEY="sk-your-key-here"
# (Legacy variables DEEPSEEK_API_KEY and OPENAI_API_KEY are also supported)
# Optional: export AI_PROVIDER=deepseek AI_BASE_URL=https://api.deepseek.com AI_MODEL=deepseek-flash

# Generate composition JSON using AI provider with auto-repair:
atari-music ai-compose \
    --provider openai \
    --model deepseek-flash \
    --style "ancient temple exploration" \
    --duration 60.0 \
    --use-16bit-bass \
    --output temple.json

# Convert validated JSON into playable WAV and 6502 assembly:
atari-music import-json temple.json --output-wav temple.wav --output-asm temple_data.asm
```

### Workflow C: Compile a Standalone Executable (XEX) for Altirra or Real Atari
```bash
# Compile composition JSON directly to XEX executable (requires MADS assembler):
atari-music build-xex temple.json -o temple.xex --player-address 0x4000 --zp-base 0x80
# Run temple.xex in Altirra or copy to SD card (SIO2SD/FujiNet) for real hardware.
```

### Workflow D: Integrating Music into an External Atari 6502 Game
1. Generate `music_data.asm` using Workflow A or B.
2. Copy `player.asm` and `music_data.asm` into your game source tree.
3. Include them in your main game file:

```asm
; --- In your game's main assembly file ---
    org $3000                   ; Game code origin

init_game:
    ; 1. Point X/Y to song data and initialize
    ldx #<song_data
    ldy #>song_data
    jsr music_init
    jsr music_play

    ; 2. Enable VBLANK interrupt or hook into your game frame loop
    cli
    rts

game_vblank_hook:
    ; 3. Call music_update ONCE every 50 Hz frame
    jsr music_update
    rts

; --- Include Player and Music Data ---
PLAYER_ZP_BASE = $80            ; Customize Zero Page if $80-$89 is occupied
    icl 'player.asm'            ; ~754 bytes code
    icl 'music_data.asm'        ; ~400-750 bytes music data
```

### Workflow E: Structural & Repetition Analysis of a Composition
```python
from atari_music.ai import load_composition_json, analyze_composition_structure

doc = load_composition_json("temple.json")
metrics = analyze_composition_structure(doc)

print(f"Repetition Ratio    : {metrics.repetition_ratio:.1%}")
print(f"Material Reuse      : {metrics.material_reuse_ratio:.1%}")
print(f"Thematic Variations : {metrics.variation_count}")
print(f"Transitions/Fills   : {metrics.transition_fill_count}")
print(f"Deduced Form        : {metrics.form.compact_form}")
print(f"Form Archetype      : {metrics.form.archetype}")
```

### Workflow F: Debugging a Failed AI Composition Request
```bash
# Run with --log-level DEBUG to view raw prompts, validation errors, and feedback:
atari-music --log-level DEBUG ai-compose \
    --provider openai \
    --model deepseek-flash \
    --style "complex jazz fusion" \
    --output debug_out.json
```

### Workflow G: Working with Music DSL (Import, Export, Compilation)
```bash
# 1. Generate Music DSL via LLM:
atari-music ai-compose --provider openai --format dsl --style "fast arcade" -o arcade.dsl

# 2. Import DSL and export both audio WAV and canonical JSON:
atari-music import-dsl arcade.dsl --output-wav arcade.wav --output-json arcade.json

# 3. Direct compilation of DSL to Atari XEX executable:
atari-music build-xex arcade.dsl --format dsl -o arcade.xex
```

```python
# Python API:
from atari_music.ai import load_composition_dsl, export_music_dsl, build_xex_from_composition

# Load and validate DSL file:
doc = load_composition_dsl("arcade.dsl")

# Export to canonical DSL string:
dsl_text = export_music_dsl(doc)

# Compile to XEX directly from DSL file:
build_xex_from_composition("arcade.dsl", output_path="arcade.xex", format="dsl")
```

---

## 12. Agent Guidance & Heuristics

When acting as an AI assistant on an Atari music task, follow these guidelines:

1. **Non-AI vs. AI Preference:**
   - If the user wants standard, deterministic, retro game chiptunes (e.g. background music for an action or dungeon game), **use Composer v4 (`atari-music compose`)**. It requires no API keys, executes instantly, and is guaranteed to pass all hardware constraints.
   - If the user wants custom styles, specific narrative moods, complex multi-thematic forms, or text-driven creativity, **use AI mode (`atari-music ai-compose`)**.
2. **Never Edit `player.asm` Internals for Song Changes:**
   - Musical changes (notes, tempo, instruments, volumes) belong in `music_data.asm` or the composition JSON. Never alter `player.asm` to modify song logic.
3. **Respect Memory Limits ($BFFF OS Boundary):**
   - On Atari XL/XE with OS enabled, user RAM ends at `$BFFF`. Ensure player and music data reside below `$C000`. Default addresses (`$4000` or `$6000`) are safe.
4. **Zero Page Allocation Safety:**
   - The player uses 10 Zero Page bytes (`PLAYER_ZP_BASE + 0..9`). If the user's project uses `$80..$89`, define `PLAYER_ZP_BASE = $90` (or another free 10-byte block in `$80..$F0`) before including `player.asm`.
5. **16-bit Bass Pairing Rules:**
   - If `use_16bit_bass` is enabled, Channel 2 is hardware-paired to Channel 1. Channel 2 **must not** contain independent note events in any pattern.
6. **MADS Dependency Awareness:**
   - Remember that compiling `.xex` binaries requires MADS. If MADS is not present in the environment, you can still generate `.wav` previews and `.asm` data files without error.
7. **Always Use `--log-level DEBUG` When Troubleshooting:**
   - If `ai-compose` fails or returns unexpected results, activate `--log-level DEBUG` to inspect the exact validation codes returned by the 3-Tier engine.
8. **Treat Logs and Artifacts as Disjoint Data Streams:**
   - In automated agent pipelines or scripts, always capture `stdout` (or file outputs) for pure composition data and direct `stderr` to operational logs. Never attempt to scrape composition data from diagnostic logs, and never expect diagnostic messages in `stdout`.

