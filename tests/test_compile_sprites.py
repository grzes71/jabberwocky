"""Tests for scripts/compile_sprites.py."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


def test_compile_sprites_real_jabberwocky(tmp_path: Path) -> None:
    """Test compiling the actual sprites/jabberwocky.json asset."""
    input_json = Path("sprites/jabberwocky.json")
    assert input_json.exists()

    out_asm = tmp_path / "dragon_sprite.asm"

    res = subprocess.run(
        [
            sys.executable,
            "scripts/compile_sprites.py",
            "--input",
            str(input_json),
            "--output",
            str(out_asm),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode == 0, f"Compilation failed: {res.stderr}"
    assert out_asm.exists()

    content = out_asm.read_text(encoding="utf-8")
    assert "DRAGON_SPRITE_W     = 8" in content
    assert "DRAGON_SPRITE_H     = 26" in content
    assert "DRAGON_FRAME_COUNT  = 8" in content
    assert "dragon_frame_0" in content
    assert "dragon_frame_7" in content
    assert "dragon_frame_tbl_lo" in content
    assert "dragon_frame_tbl_hi" in content


def test_compile_sprites_validation_error(tmp_path: Path) -> None:
    """Test that invalid frame height raises an error."""
    bad_json = tmp_path / "bad.json"
    bad_json.write_text(
        json.dumps({
            "version": 1,
            "sprites": [{
                "id": "BAD",
                "width": 8,
                "height": 4,
                "frames": [{"pixels": ["00000000", "11111111"]}]  # only 2 lines instead of 4
            }]
        }),
        encoding="utf-8",
    )

    res = subprocess.run(
        [
            sys.executable,
            "scripts/compile_sprites.py",
            "-i",
            str(bad_json),
            "-o",
            str(tmp_path / "out.asm"),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode != 0
    assert "height mismatch" in res.stderr
