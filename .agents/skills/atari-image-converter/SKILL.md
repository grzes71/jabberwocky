---
name: atari-image-converter
description: >-
  Use when working on the Atari Image Converter project (py-image-converter):
  a modular Python pipeline that converts modern images into Atari 8-bit
  ANTIC Mode E graphics with dithering, palette selection, quality metrics,
  and multi-format export.
---

# Atari Image Converter — Agent Skill

> **Type:** Project-specific domain skill
> **Purpose:** Guide AI agents working on the `py-image-converter` codebase.
> Load this skill when asked to add features, fix bugs, refactor, review,
> or explain any part of this project.

---

## 1. Project Identity

- **Name:** `atari-image-converter` (pip package) / `py-image-converter` (repo)
- **Language:** Python 3.12+
- **Location:** `src/converter/` (all source), `src/tests/` (all tests)
- **Entry points:**
  - `convert.py` — thin CLI wrapper (adds `src/` to `sys.path`, calls `main()`)
  - `python -m converter.main` — direct module invocation
  - `atari-convert` — registered console script (from `pyproject.toml`)
- **Dependencies:** `numpy>=1.26`, `Pillow>=10.0` (runtime); `pytest>=8.0`, `ruff>=0.4` (dev)
- **Linter:** `ruff` (line-length=100, target python 3.12)
- **Versioning:** `setuptools-scm`, tag-driven (`vX.Y.Z`), no static version in `pyproject.toml`
- **Build:** `python -m build` → `.whl` + `.tar.gz`

---

## 2. Architecture Overview

The project is a **fully decoupled image processing pipeline**. Each stage is
a separate module that takes typed inputs and returns typed outputs.
The central orchestrator is `pipeline.py`.

### 2.1 Pipeline Stages (in order)

```
Input Image → Resize → Sharpen → Histogram/Variance → Palette Select
→ Edge Detect → Dither/Quantize → Metrics → Export (PNG/BIN/ASM/DTA/XEX)
```

| Stage | Module | Key Function(s) |
|:---|:---|:---|
| Load | `image_loader.py` | `load_image()` → `ImageBuffer` |
| Resize | `resize.py` | `resize_nearest/bilinear/bicubic/lanczos()` |
| Sharpen | `sharpen.py` | `unsharp_mask()`, `apply_sharpen()` |
| Histogram | `histogram.py` | `analyze_histogram()` → `HistogramReport` |
| Palette | `palette.py` | `select_palette()`, `palette_rgb()` |
| Edge detect | `edge_detect.py` | `sobel_edges()`, `laplacian_edges()`, `detect_edges()` |
| Dithering | `dithering.py` | `apply_dithering()`, `get_dither_algorithm()` |
| Quantize | `quantizer.py` | `quantize_nearest/perceptual/weighted/adaptive()` |
| Metrics | `metrics.py` | `compute_mse/psnr/ssim()`, `format_metrics()` |
| Preview | `preview.py` | `generate_previews()` |
| Export | `exporters/` | `export_png/basin/dta/xex()` |

### 2.2 Key Data Types (`types.py`)

| Type | Purpose |
|:---|:---|
| `RGBImage` | `NDArray[np.uint8]`, shape `(H, W, 3)` — standard image representation |
| `FloatImage` | `NDArray[np.float64]` — floating-point image data |
| `IndexedImage` | `NDArray[np.uint8]` — palette-indexed output (values 0..N) |
| `EdgeMask` | `NDArray[np.float64]` — normalized 0-1 edge magnitudes |
| `ImageBuffer` | Wrapper: `.data` (RGBImage), `.height`, `.width`, `.shape` |
| `AtariColor` | Single palette entry: `.index`, `.rgb`, `.hsv`, `.luminance`, `.name` |
| `HistogramReport` | `.rgb_histogram`, `.local_variance`, `.gradient_magnitude`, `.detail_score` |
| `MetricResult` | `.mse`, `.psnr`, `.ssim`, `.mean_rgb_error`, `.mean_luminance_error`, `.colors_used`, `.histogram_coverage` |
| `ConversionResult` | `.indexed`, `.palette_indices`, `.palette_rgb`, `.source_resized`, `.metrics` |
| `ConversionConfig` | All CLI/JSON settings; has `.to_dict()` / `.from_dict()` |

### 2.3 Enums (also in `types.py`)

| Enum | Values |
|:---|:---|
| `AtariMode` | `ANTIC_E` |
| `ResizeMethod` | `nearest`, `bilinear`, `bicubic`, `lanczos` |
| `DitherMethod` | `none`, `floyd`, `jarvis`, `stucki`, `sierra`, `sierra_lite`, `burkes`, `atkinson`, `bayer2`, `bayer4`, `bayer8`, `adaptive` |
| `PaletteMethod` | `popularity`, `kmeans`, `median_cut`, `octree`, `perceptual` |
| `QuantizerMethod` | `nearest`, `perceptual`, `weighted`, `adaptive` |
| `ExportFormat` | `png`, `bin`, `asm`, `dta`, `xex` |

---

## 3. Coding Conventions

### 3.1 Module Structure

- Every `.py` file starts with `from __future__ import annotations`.
- Docstrings are short (`"""Description."""`) at module and function level.
- Type hints are used throughout; custom types are aliased in `types.py`.
- All image data flows as NumPy arrays (`RGBImage`, `IndexedImage`, etc.).
- Float operations use `np.float64`; output is clipped and cast back to `np.uint8`.

### 3.2 Adding a New Dither Algorithm

1. Create `src/converter/algorithms/<name>.py`.
2. Subclass `DitherAlgorithm` (from `algorithms/base.py`).
3. Implement `apply(self, image, palette_rgb, edge_mask) -> IndexedImage`.
4. Set `name` class attribute.
5. Register in `dithering.py` → `_DITHER_REGISTRY` dict.

### 3.3 Adding a New Palette Selector

1. In `palette.py`, subclass `PaletteSelector`.
2. Implement `select(self, image, count, background_index) -> list[int]`.
3. Add the new enum value to `PaletteMethod` in `types.py`.
4. Wire it into `select_palette()` in `palette.py`.

### 3.4 Adding a New Quantizer

1. Add a `quantize_<name>()` function in `quantizer.py`.
2. Add the enum value to `QuantizerMethod`.
3. Wire it into the `quantize()` dispatch function.

### 3.5 Adding a New Exporter

1. Create `exporters/<format>_export.py`.
2. Implement `export_<format>(result, output_path, config)`.
3. Add enum value to `ExportFormat`.
4. Register in `pipeline.py` → `export_result()`.

### 3.6 Adding a New Resize Method

1. Add function in `resize.py`.
2. Add enum value to `ResizeMethod`.
3. Wire into `resize_image()` dispatch.

---

## 4. Configuration Flow

```
CLI args → argparse → ConversionConfig dataclass → pipeline.run_conversion()
          ↑                                              ↓
    --config (JSON)                              export_result()
          ↑                                              ↓
    --save-config (JSON)                          [PNG, BIN, ASM, DTA, XEX]
```

- `ConversionConfig.from_dict()` handles JSON deserialization.
- `ConversionConfig.to_dict()` handles serialization.
- CLI args override JSON config values (JSON loaded first, then CLI applied).

---

## 5. Atari-Specific Knowledge

### 5.1 ANTIC Mode E

- Resolution: 160×192 pixels
- Color depth: 2 bits per pixel (4 colors, indices 0–3)
- One color is the background (COLBAK / PM0 at index 0)
- Pixel pairs packed into one byte: `byte = (pixel2 << 2) | pixel1` (left pixel in low 2 bits)
- Screen memory size: 40 bytes/line × 192 lines = 7680 bytes (but typically padded to 8 KB for 4K boundary alignment)

### 5.2 Atari Palette (`atari_palette.py`)

- 256 colors total (16 hues × 16 luminance levels)
- Index = `hue * 16 + luminance`
- `PALETTE` is a list of `AtariColor` objects with `.index`, `.rgb`, `.hsv`, `.luminance`, `.name`
- `get_color(index)` returns `AtariColor`
- Colors are pre-computed with pairwise distances for fast lookup

### 5.3 XEX Export

- Produces a self-contained Atari executable
- Includes: display list, screen data, and a small loader
- Default memory layout: VRAM at `$4000`, display list at `$3E00`, init at `$3800`
- Header uses `$FF $FF` magic bytes

---

## 6. Testing

### 6.1 Running Tests

```bash
pytest                          # all tests
pytest src/tests/test_floyd.py  # specific test file
pytest -k "dither"              # tests matching keyword
```

### 6.2 Test Conventions

- Tests live in `src/tests/` (not top-level `tests/`).
- Fixtures and baselines in `src/tests/fixtures/`.
- Integration tests: `test_integration.py`.
- Regression tests compare against `baselines.json`.
- Tests use `ConversionConfig` directly (not CLI) for unit-level testing.
- Common pattern: create a small synthetic NumPy image, run one pipeline stage, assert output shape/values.

---

## 7. Batch Generation

The `generate-images.ps1` PowerShell script generates all combinations of:
- 5 palettes × 12 dithers × 4 resizes × 4 quantizers = 960 variants

It sets `$env:PYTHONPATH = "src"` and invokes `python -m converter.main` for each.

Output files use naming convention:
```
<basename>-p_<palette>-d_<dither>-r_<resize>-q_<quantizer>.png
```

---

## 8. GitHub Actions / Release

- Workflow: `.github/workflows/release-on-pr-close.yml`
- Trigger: PR closed (merged into `main`)
- Calculates next semver from commit messages (conventional commits)
- Creates and pushes tag, then builds with `python -m build`
- Publishes `.whl` and `.tar.gz` as GitHub Release assets

---

## 9. Common Tasks Cheat Sheet

| Task | Where to look / What to do |
|:---|:---|
| Add CLI flag | `main.py` → `build_parser()`, then `types.py` → `ConversionConfig` |
| Change default settings | `types.py` → `ConversionConfig` field defaults |
| Add a new dither algorithm | `algorithms/<name>.py` → subclass `DitherAlgorithm` → register in `dithering.py` |
| Add a new palette method | `palette.py` → subclass `PaletteSelector` → add enum → wire in `select_palette()` |
| Add a new export format | `exporters/<format>_export.py` → add enum → wire in `pipeline.py` |
| Fix color matching | `quantizer.py` |
| Improve edge detection | `edge_detect.py` |
| Fix metrics calculation | `metrics.py` |
| Debug pipeline issue | `pipeline.py` → `convert_image()` — trace stage by stage |
| Run all tests | `pytest` from repo root |
| Lint code | `ruff check src/` |
| Build package | `python -m build` |
| Install dev deps | `pip install -e ".[dev]"` |

---

## 10. Important Constraints

- **NumPy-only image processing** — Pillow is used ONLY for I/O (`image_loader.py`, `png_export.py`, `preview.py`). All pixel manipulation must use NumPy.
- **RGB (H, W, 3) uint8** — the canonical in-memory format throughout the pipeline.
- **No OpenCV** — the project deliberately avoids heavy external dependencies.
- **Python 3.12+** — use modern syntax (`X | Y` unions, PEP 695 if needed).
- **Ruff formatting** — line length 100, target version py312.
- **All new features need tests** — add test file in `src/tests/` or extend existing ones.
- **Backward compatibility** — changes to `ConversionConfig` fields or enums may break config files and CLI users; prefer adding new values over renaming existing ones.
