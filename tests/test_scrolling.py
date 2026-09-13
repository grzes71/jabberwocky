"""Unit and py65 integration tests for horizontal playfield scrolling and level progression."""

from pathlib import Path
import re
from typing import Dict
import pytest
from py65.devices.mpu6502 import MPU


def parse_labels(lab_path: Path) -> Dict[str, int]:
    """Parse MADS label (.lab) file into a mapping of symbol name -> address."""
    labels: Dict[str, int] = {}
    pattern = re.compile(r"^[0-9a-fA-F]{2}\t([0-9a-fA-F]{4})\t([A-Za-z0-9_@?.]+)")
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


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def labels(project_root: Path) -> Dict[str, int]:
    lab_file = project_root / "gen" / "jabberwocky.lab"
    assert lab_file.exists(), "gen/jabberwocky.lab must exist (run make all)"
    return parse_labels(lab_file)


def run_subroutine(mpu: MPU, target_addr: int, max_steps: int = 100000) -> None:
    """Execute a subroutine at target_addr until it executes RTS back to $0100."""
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00  # BRK
    mpu.pc = target_addr

    steps = 0
    while mpu.pc != 0x0100 and steps < max_steps:
        mpu.step()
        steps += 1

    assert mpu.pc == 0x0100, f"Routine at {hex(target_addr)} did not return within {max_steps} steps (PC={hex(mpu.pc)})"


def test_scrolling_symbols_exist(labels: Dict[str, int]):
    """Verify that all scrolling and level progression symbols exist in label table."""
    expected_symbols = [
        "INIT_LEVEL_SCREENS",
        "SETUP_INCOMING_SCREEN_PTR",
        "UPDATE_WORLD_SCROLLING",
        "SHIFT_VRAM_LEFT",
        "SCROLL_PLAYFIELD_STEP",
        "ADVANCE_TO_NEXT_LEVEL",
        "REASON_SUCCESS",
        "CURRENT_LEVEL_IDX",
        "LEVEL_SCREEN_POS",
        "LAB_TOTAL_SCREENS",
        "INCOMING_COL_IDX",
        "LEVEL_TAIL_COLS",
        "SCROLL_ACCUM_LO",
        "SCROLL_ACCUM_HI",
        "HSCROL_FINE",
        "INCOMING_SCREEN_PTR",
    ]
    for sym in expected_symbols:
        assert sym in labels, f"Expected symbol {sym} not found in label table"


def test_shift_vram_left_emulation(project_root: Path, labels: Dict[str, int]):
    """Test that shift_vram_left shifts all 11 rows of 48 bytes left by 1 column."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_addr = labels["GAME_ACTION_VRAM"]

    # Fill 11 rows (528 bytes, 48 bytes per row) with distinct recognizable byte pattern
    for r in range(11):
        for c in range(48):
            mpu.memory[vram_addr + r * 48 + c] = (r * 48 + c + 1) & 0xFF

    run_subroutine(mpu, labels["SHIFT_VRAM_LEFT"])

    # Verify that columns 0..46 shifted left by 1 column
    for r in range(11):
        for c in range(47):
            expected = (r * 48 + (c + 1) + 1) & 0xFF
            actual = mpu.memory[vram_addr + r * 48 + c]
            assert actual == expected, f"Row {r} col {c}: expected {expected}, got {actual}"


def test_init_level_screens_emulation(project_root: Path, labels: Dict[str, int]):
    """Test that init_level_screens preloads screen 0 into visible cols 4..43 and primes screen 1."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Verify state variables
    assert mpu.memory[labels["CURRENT_LEVEL_IDX"]] == 0
    assert mpu.memory[labels["LEVEL_SCREEN_POS"]] == 1
    assert mpu.memory[labels["INCOMING_COL_IDX"]] == 4  # First 4 cols prefilled into cols 44..47
    assert mpu.memory[labels["LEVEL_TAIL_COLS"]] == 0
    assert mpu.memory[labels["LAB_TOTAL_SCREENS"]] >= 8
    assert mpu.memory[labels["HSCROL_FINE"]] == 3

    # Check that visible columns 4..43 match Screen 0
    screen0_vram = labels["SCREEN_FOREST_01_VRAM"]
    screen0_blk = labels["SCREEN_FOREST_01_BLOCKING"]
    action_vram = labels["GAME_ACTION_VRAM"]
    for r in range(11):
        for c in range(40):
            expected = mpu.memory[screen0_vram + r * 40 + c]
            actual = mpu.memory[action_vram + r * 48 + 4 + c]
            assert actual == expected, f"Row {r} visible col {c}: expected {expected}, got {actual}"

    # Check that right margin columns 44..47 match cols 0..3 of Screen 1
    screen1_vram = labels["SCREEN_FOREST_02_VRAM"]
    for r in range(11):
        for c in range(4):
            expected = mpu.memory[screen1_vram + r * 40 + c]
            actual = mpu.memory[action_vram + r * 48 + 44 + c]
            assert actual == expected, f"Row {r} margin col {c}: expected {expected}, got {actual}"

    # Check that dragon blocking columns match cols 4 and 5 of Screen 0
    col8_base = labels["BLOCKING_COL8"]
    col9_base = labels["BLOCKING_COL9"]
    for r in range(11):
        assert mpu.memory[col8_base + r] == mpu.memory[screen0_blk + r * 40 + 4], f"Row {r} col 8 blocking mismatch"
        assert mpu.memory[col9_base + r] == mpu.memory[screen0_blk + r * 40 + 5], f"Row {r} col 9 blocking mismatch"


def test_scroll_playfield_step_streams_column(project_root: Path, labels: Dict[str, int]):
    """Test that scroll_playfield_step injects column 4 of screen 1 into column 47 of VRAM and shifts blocking cols."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Run 1 scroll step (coarse shift)
    run_subroutine(mpu, labels["SCROLL_PLAYFIELD_STEP"])

    assert mpu.memory[labels["INCOMING_COL_IDX"]] == 5

    # Check that column 47 in each row equals column 4 from screen 1 (screen_FOREST_02_vram)
    screen0_blk = labels["SCREEN_FOREST_01_BLOCKING"]
    screen1_vram = labels["SCREEN_FOREST_02_VRAM"]
    action_vram = labels["GAME_ACTION_VRAM"]
    for r in range(11):
        expected_char = mpu.memory[screen1_vram + r * 40 + 4]  # col 4 of row r
        actual_char = mpu.memory[action_vram + r * 48 + 47]  # col 47 of row r
        assert actual_char == expected_char, f"Row {r} col 47: expected {expected_char}, got {actual_char}"

    # Check that dragon blocking columns shifted: col 8 gets col 5, col 9 gets col 6 of Screen 0
    col8_base = labels["BLOCKING_COL8"]
    col9_base = labels["BLOCKING_COL9"]
    for r in range(11):
        assert mpu.memory[col8_base + r] == mpu.memory[screen0_blk + r * 40 + 5], f"Row {r} col 8 shifted mismatch"
        assert mpu.memory[col9_base + r] == mpu.memory[screen0_blk + r * 40 + 6], f"Row {r} col 9 shifted mismatch"


def test_update_world_scrolling_fine_scroll(project_root: Path, labels: Dict[str, int]):
    """Test hardware fine scroll decrementing and coarse shift triggering."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Set speed to exactly 1 color clock per frame ($0100)
    mpu.memory[labels["SCROLL_SPEED"]] = 0x00
    mpu.memory[labels["SCROLL_SPEED"] + 1] = 0x01

    # Frame 1: accum = $0100, fine scroll = 3 - 1 = 2
    run_subroutine(mpu, labels["UPDATE_WORLD_SCROLLING"])
    assert mpu.memory[labels["HSCROL_FINE"]] == 2

    # Frame 2: accum = $0200, fine scroll = 3 - 2 = 1
    run_subroutine(mpu, labels["UPDATE_WORLD_SCROLLING"])
    assert mpu.memory[labels["HSCROL_FINE"]] == 1

    # Frame 3: accum = $0300, fine scroll = 3 - 3 = 0
    run_subroutine(mpu, labels["UPDATE_WORLD_SCROLLING"])
    assert mpu.memory[labels["HSCROL_FINE"]] == 0

    # Frame 4: accum reaches $0400 (threshold) -> coarse shift, fine scroll wraps to 3
    run_subroutine(mpu, labels["UPDATE_WORLD_SCROLLING"])
    assert mpu.memory[labels["HSCROL_FINE"]] == 3
    assert mpu.memory[labels["INCOMING_COL_IDX"]] == 5  # Coarse step advanced col idx from 4 to 5


def test_level_completion_and_victory_transition(project_root: Path, labels: Dict[str, int]):
    """Test that scrolling past all screens + 48 tail columns triggers REASON_SUCCESS."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Fast-forward to last tail column
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 3
    mpu.memory[labels["INCOMING_COL_IDX"]] = 0
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 1
    mpu.memory[labels["GAME_OVER_REASON"]] = 0

    # Running one more scroll step should decrement level_tail_cols to 0 and call advance_to_next_level
    run_subroutine(mpu, labels["SCROLL_PLAYFIELD_STEP"])

    reason_success = labels["REASON_SUCCESS"]
    assert reason_success == 4
    actual_reason = mpu.memory[labels["GAME_OVER_REASON"]]
    assert actual_reason == reason_success, f"GAME_OVER_REASON should be {reason_success} (SUCCESS), got {actual_reason}"


def test_dragon_respawn_restarts_level_from_beginning(project_root: Path, labels: Dict[str, int]):
    """Verify that when dragon dies, respawn_dragon restarts the current level from screen 0."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Simulate scrolled playfield deep into the level
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 2
    mpu.memory[labels["INCOMING_COL_IDX"]] = 25
    mpu.memory[labels["HSCROL_FINE"]] = 1
    mpu.memory[labels["SCROLL_SPEED"]] = 0x00
    mpu.memory[labels["SCROLL_SPEED"] + 1] = 0x03
    mpu.memory[labels["COUNTER_FULL"]] = 5

    # Overwrite VRAM with dirty bytes
    action_vram = labels["GAME_ACTION_VRAM"]
    for i in range(528):
        mpu.memory[action_vram + i] = 0xFF

    # Execute respawn_dragon
    run_subroutine(mpu, labels["RESPAWN_DRAGON"])

    # Verify that the level has been restarted from screen 0
    assert mpu.memory[labels["CURRENT_LEVEL_IDX"]] == 0
    assert mpu.memory[labels["LEVEL_SCREEN_POS"]] == 1
    assert mpu.memory[labels["INCOMING_COL_IDX"]] == 4
    assert mpu.memory[labels["LEVEL_TAIL_COLS"]] == 0
    assert mpu.memory[labels["HSCROL_FINE"]] == 3

    # Scroll speed reset to base speed
    base_speed = labels["SCROLL_BASE_SPEED"]
    actual_speed = mpu.memory[labels["SCROLL_SPEED"]] | (mpu.memory[labels["SCROLL_SPEED"] + 1] << 8)
    assert actual_speed == base_speed

    # Energy bar refilled to 40
    assert mpu.memory[labels["COUNTER_FULL"]] == 40

    # Dragon restored to start position
    assert mpu.memory[labels["DRAGON_X"]] == labels["DRAGON_START_X"]
    assert mpu.memory[labels["DRAGON_Y"]] == labels["DRAGON_START_Y"]

    # Playfield reloaded with screen 0
    screen0_vram = labels["SCREEN_FOREST_01_VRAM"]
    for r in range(11):
        for c in range(40):
            expected = mpu.memory[screen0_vram + r * 40 + c]
            actual = mpu.memory[action_vram + r * 48 + 4 + c]
            assert actual == expected, f"Row {r} col {c} not reset to screen 0"

