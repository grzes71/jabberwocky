"""Unit and py65 integration tests for bottom status bar (LEVEL, SCORE, LIVES)."""

from pathlib import Path
import re
from typing import Dict, List
import pytest
from py65.devices.mpu6502 import MPU


def parse_labels(lab_path: Path) -> Dict[str, int]:
    """Parse MADS label (.lab) file into a mapping of symbol name -> address."""
    labels: Dict[str, int] = {}
    pattern = re.compile(r"^[0-9a-fA-F]{2}\t([0-9a-fA-F]{4})\t([A-Za-z0-9_@?]+)")
    with open(lab_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line)
            if m:
                labels[m.group(2).upper()] = int(m.group(1), 16)
    return labels


def load_xex(xex_path: Path, memory: bytearray) -> None:
    """Load Atari DOS executable (.xex) segments into memory array."""
    data = xex_path.read_bytes()
    idx = 0
    if len(data) >= 2 and data[0] == 0xFF and data[1] == 0xFF:
        idx = 2

    while idx < len(data):
        if idx + 4 > len(data):
            break
        if data[idx] == 0xFF and data[idx + 1] == 0xFF:
            idx += 2
            continue
        start = data[idx] | (data[idx + 1] << 8)
        end = data[idx + 2] | (data[idx + 3] << 8)
        idx += 4
        length = end - start + 1
        block = data[idx : idx + length]
        idx += length
        for i, b in enumerate(block):
            memory[start + i] = b


def antic_inv_to_ascii(code: int) -> str:
    """Convert an inverted ANTIC display code (with bit 7 = 1) to ASCII character."""
    assert code & 0x80, f"Expected inverted display code with bit 7 set, got {hex(code)}"
    c = code & 0x7F
    if 0 <= c <= 31:  # Space, punctuation, digits
        return chr(c + 32)
    elif 32 <= c <= 95:  # Uppercase and symbols
        return chr(c + 32)
    elif 96 <= c <= 127:  # Lowercase
        return chr(c)
    return "?"


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def labels(project_root: Path) -> Dict[str, int]:
    lab_file = project_root / "gen" / "jabberwocky.lab"
    assert lab_file.exists(), "gen/jabberwocky.lab must exist (run make all)"
    return parse_labels(lab_file)


def test_status_symbols_exist(labels: Dict[str, int]):
    """Verify that LEVEL, LIVES, and SCORE memory cells are defined."""
    assert "LEVEL" in labels, "LEVEL symbol not found in label table"
    assert "LIVES" in labels, "LIVES symbol not found in label table"
    assert "SCORE" in labels, "SCORE symbol not found in label table"
    assert "DRAW_BOTTOM_STATUS" in labels
    assert "UPDATE_BOTTOM_STATUS" in labels


def test_initial_values_in_xex(project_root: Path, labels: Dict[str, int]):
    """Verify initial memory values: LEVEL=1, LIVES=3, SCORE=6 zeroes."""
    xex_path = project_root / "jabberwocky.xex"
    memory = bytearray(65536)
    load_xex(xex_path, memory)

    level_addr = labels["LEVEL"]
    lives_addr = labels["LIVES"]
    score_addr = labels["SCORE"]

    assert memory[level_addr] == 1, f"LEVEL initial value should be 1, got {memory[level_addr]}"
    assert memory[lives_addr] == 3, f"LIVES initial value should be 3, got {memory[lives_addr]}"
    score_bytes = [memory[score_addr + i] for i in range(6)]
    assert score_bytes == [0, 0, 0, 0, 0, 0], f"SCORE initial value should be 6 zeroes, got {score_bytes}"


def test_draw_bottom_status_emulation(project_root: Path, labels: Dict[str, int]):
    """Emulate draw_bottom_status and verify initial display in VRAM."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_status_row1 = labels["GAME_STATUS_VRAM"] + 40

    # Clear status row with 0 before running
    for i in range(40):
        mpu.memory[vram_status_row1 + i] = 0

    # Set up return address on stack ($0100) and BRK ($00) at $0100
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DRAW_BOTTOM_STATUS"]

    steps = 0
    while mpu.pc != 0x0100 and steps < 5000:
        mpu.step()
        steps += 1

    assert mpu.pc == 0x0100, f"Routine did not return within 5000 steps, PC={hex(mpu.pc)}"

    row1_bytes = [mpu.memory[vram_status_row1 + i] for i in range(40)]
    decoded_str = "".join(antic_inv_to_ascii(b) for b in row1_bytes)

    expected = " LEVEL: 1     SCORE: 000000    LIVES: 3 "
    assert decoded_str == expected, f"VRAM row 1 mismatch:\nExpected: '{expected}'\nGot:      '{decoded_str}'"


def test_update_bottom_status_dynamic(project_root: Path, labels: Dict[str, int]):
    """Verify update_bottom_status dynamically reflects changes in LEVEL, SCORE, LIVES."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_status_row1 = labels["GAME_STATUS_VRAM"] + 40

    # First draw the template
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DRAW_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    # Change memory values
    level_addr = labels["LEVEL"]
    lives_addr = labels["LIVES"]
    score_addr = labels["SCORE"]

    mpu.memory[level_addr] = 5
    mpu.memory[lives_addr] = 2
    for i, digit in enumerate([1, 2, 3, 4, 5, 6]):
        mpu.memory[score_addr + i] = digit

    # Call update_bottom_status
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.pc = labels["UPDATE_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    row1_bytes = [mpu.memory[vram_status_row1 + i] for i in range(40)]
    decoded_str = "".join(antic_inv_to_ascii(b) for b in row1_bytes)

    expected = " LEVEL: 5     SCORE: 123456    LIVES: 2 "
    assert decoded_str == expected, f"VRAM row 1 dynamic update mismatch:\nExpected: '{expected}'\nGot:      '{decoded_str}'"


def test_bottom_bar_sprites_config(project_root: Path, labels: Dict[str, int]):
    """Verify sprite position and color memory cells for bottom status bar."""
    assert "BOT_BAR_P0_X" in labels
    assert "BOT_BAR_P1_X" in labels
    assert "BOT_BAR_P2_X" in labels
    assert "BOT_BAR_PMG_Y" in labels
    assert "PAL_BOTTOM_P0" in labels
    assert "PAL_BOTTOM_P1" in labels
    assert "PAL_BOTTOM_P2" in labels

    xex_path = project_root / "jabberwocky.xex"
    memory = bytearray(65536)
    load_xex(xex_path, memory)

    assert memory[labels["BOT_BAR_P0_X"]] == 48
    assert memory[labels["BOT_BAR_P1_X"]] == 100
    assert memory[labels["BOT_BAR_P2_X"]] == 168
    assert memory[labels["BOT_BAR_PMG_Y"]] == 218

    assert memory[labels["PAL_BOTTOM_P0"]] == 0xA0  # Cyan
    assert memory[labels["PAL_BOTTOM_P1"]] == 0x40  # Pink
    assert memory[labels["PAL_BOTTOM_P2"]] == 0x10  # Yellow


