"""Tests for scripts/generate_memory_map.py."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest


def test_parse_real_jabberwocky_lab_and_lst(tmp_path: Path) -> None:
    """Test parsing real Jabberwocky MADS outputs (gen/jabberwocky.lab + lst)."""
    input_lab = Path("gen/jabberwocky.lab")
    assert input_lab.exists(), "gen/jabberwocky.lab must exist for integration test"

    out_txt = tmp_path / "memory_map.txt"
    out_json = tmp_path / "memory_map.json"

    res = subprocess.run(
        [
            sys.executable,
            "scripts/generate_memory_map.py",
            "--input",
            str(input_lab),
            "--out-text",
            str(out_txt),
            "--out-json",
            str(out_json),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode == 0, f"Process failed: {res.stderr}"
    assert out_txt.exists()
    assert out_json.exists()

    # Verify JSON structure
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 7

    # Check required keys in every segment
    for seg in data:
        assert "name" in seg
        assert "start_address" in seg
        assert "end_address" in seg
        assert "size" in seg
        assert "type" in seg
        assert seg["size"] > 0

    # Check specific known segments
    seg_names = [s["name"] for s in data]
    assert "RUNAD" in seg_names
    assert "CODE" in seg_names
    assert "DLIST" in seg_names
    assert "VRAM" in seg_names
    assert "FONT" in seg_names
    assert "FREE_SPACE" in seg_names

    # Check text output
    txt_content = out_txt.read_text(encoding="utf-8")
    assert "ZERO PAGE USAGE" in txt_content
    assert "PTR_SRC" in txt_content
    assert "PTR_DST" in txt_content
    assert "ZP_TMP" in txt_content
    assert "FREE ZERO PAGE: $85 - $FF" in txt_content
    assert re.search(r"FREE SPACE: \$[0-9A-F]{4} - \$3FFF", txt_content)
    assert re.search(r"FREE SPACE: \$[0-9A-F]{4} - \$6[0-9A-F]{3}", txt_content)
    assert re.search(r"FREE SPACE: \$[0-9A-F]{4} - \$BFFF", txt_content)
    assert "VALIDATION PASSED" in txt_content


def test_parse_sample_lab_and_calculate_gaps(tmp_path: Path) -> None:
    """Test parsing a standalone .lab file and accurately calculating gaps."""
    sample_lab = tmp_path / "sample.lab"
    sample_lab.write_text(
        """mads 2.1.7 build 21
Label table:
00	0080	PTR_SRC
00	0082	PTR_DST
00	0084	ZP_TMP
00	2000	BLOCK1_START
00	2500	BLOCK1_END
00	3000	BLOCK2_START
00	3800	BLOCK2_END
""",
        encoding="utf-8",
    )

    out_txt = tmp_path / "map.txt"
    out_json = tmp_path / "map.json"

    res = subprocess.run(
        [
            sys.executable,
            "scripts/generate_memory_map.py",
            "--input",
            str(sample_lab),
            "--out-text",
            str(out_txt),
            "--out-json",
            str(out_json),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode == 0, f"Failed: {res.stderr}"

    data = json.loads(out_json.read_text(encoding="utf-8"))
    # Expected layout ($0800-$BFFF):
    # Free gap 1: $0800 - $1FFF (size: 0x1FFF - 0x0800 + 1 = 6144)
    # BLOCK1: $2000 - $2500 (size: 1281)
    # Free gap 2: $2501 - $2FFF (size: 0x2FFF - 0x2501 + 1 = 2815)
    # BLOCK2: $3000 - $3800 (size: 2049)
    # Free gap 3: $3801 - $BFFF (size: 0xBFFF - 0x3801 + 1 = 34815)
    free_gaps = [s for s in data if s["type"] == "free"]
    assert len(free_gaps) == 3

    assert free_gaps[0]["start_address"] == "$0800"
    assert free_gaps[0]["end_address"] == "$1FFF"
    assert free_gaps[0]["size"] == 6144

    assert free_gaps[1]["start_address"] == "$2501"
    assert free_gaps[1]["end_address"] == "$2FFF"
    assert free_gaps[1]["size"] == 2815

    assert free_gaps[2]["start_address"] == "$3801"
    assert free_gaps[2]["end_address"] == "$BFFF"
    assert free_gaps[2]["size"] == 34815


def test_fails_on_artificial_collision(tmp_path: Path) -> None:
    """Test that introducing an artificial overlap/collision causes exit code > 0."""
    collision_lab = tmp_path / "collision.lab"
    collision_lab.write_text(
        """mads 2.1.7
Label table:
00	2000	SEG_A_START
00	2600	SEG_A_END
00	2400	SEG_B_START
00	3000	SEG_B_END
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [
            sys.executable,
            "scripts/generate_memory_map.py",
            "--input",
            str(collision_lab),
            "--out-text",
            str(tmp_path / "out.txt"),
            "--out-json",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode != 0, "Script should fail when segment collision is detected"
    assert "Memory segment overlap detected" in res.stderr
    assert "SEG_A" in res.stderr
    assert "SEG_B" in res.stderr


def test_fails_on_user_variable_in_os_zero_page(tmp_path: Path) -> None:
    """Test that mapping a user variable to OS Zero Page ($00-$7F) causes exit code > 0."""
    zp_violation_lab = tmp_path / "zp_violation.lab"
    zp_violation_lab.write_text(
        """mads 2.1.7
Label table:
00	0020	ZP_USER_POS_X
00	0080	PTR_SRC
00	3000	START
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [
            sys.executable,
            "scripts/generate_memory_map.py",
            "--input",
            str(zp_violation_lab),
            "--out-text",
            str(tmp_path / "out.txt"),
            "--out-json",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode != 0, "Script should fail when user variable is in OS Zero Page"
    assert "Zero page violation" in res.stderr
    assert "ZP_USER_POS_X" in res.stderr
    assert "$20" in res.stderr


def test_fails_on_os_rom_boundary_exceeded(tmp_path: Path) -> None:
    """Test that a segment exceeding $BFFF causes exit code > 0."""
    rom_violation_lab = tmp_path / "rom_violation.lab"
    rom_violation_lab.write_text(
        """mads 2.1.7
Label table:
00	B000	BUFFER_START
00	C400	BUFFER_END
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [
            sys.executable,
            "scripts/generate_memory_map.py",
            "--input",
            str(rom_violation_lab),
            "--out-text",
            str(tmp_path / "out.txt"),
            "--out-json",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode != 0, "Script should fail when user RAM segment crosses $BFFF boundary"
    assert "Memory boundary violation" in res.stderr
    assert "$C400" in res.stderr
