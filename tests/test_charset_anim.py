"""Unit and py65 emulation tests for charset animation subsystem (Jabberwocky)."""

from pathlib import Path
import re
from typing import Dict, List
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


def run_subroutine(mpu: MPU, target_addr: int, max_steps: int = 100000) -> None:
    """Execute a subroutine at target_addr until it returns via RTS."""
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)  # RTS return address ($0100)
    mpu.pc = target_addr
    steps = 0
    while steps < max_steps:
        if mpu.pc == 0x0100:
            return
        mpu.step()
        steps += 1
    raise TimeoutError(f"Subroutine at ${target_addr:04X} exceeded {max_steps} steps without RTS")


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def labels(project_root: Path) -> Dict[str, int]:
    lab_file = project_root / "gen" / "jabberwocky.lab"
    assert lab_file.exists(), "gen/jabberwocky.lab must exist (run make all)"
    return parse_labels(lab_file)


def test_charset_animation_symbols_and_config(project_root: Path, labels: Dict[str, int]) -> None:
    """Verify all symbols, counts, and destination pointers exist and are correctly aligned."""
    assert "ANIM_CHAR_COUNT" in labels
    assert labels["ANIM_CHAR_COUNT"] == 2
    assert "NUM_ANIM_CHARS" in labels
    assert labels["NUM_ANIM_CHARS"] == 6

    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    dest_lo_base = labels["ANIMATED_CHAR_DEST_LO"]
    dest_hi_base = labels["ANIMATED_CHAR_DEST_HI"]
    ids_base = labels["ANIMATED_CHAR_IDS"]

    for idx in range(6):
        char_id = mpu.memory[ids_base + idx]
        expected_addr = 0x7400 + char_id * 8
        lo = mpu.memory[dest_lo_base + idx]
        hi = mpu.memory[dest_hi_base + idx]
        actual_addr = lo | (hi << 8)
        assert actual_addr == expected_addr, f"Char {char_id} dest addr mismatch"


def test_init_charset_animation_emulation(project_root: Path, labels: Dict[str, int]) -> None:
    """Verify init_charset_animation resets all timers, frame pointers, and segment states."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    # Corrupt state variables
    for i in range(2):
        mpu.memory[labels["ANIM_CHAR_COUNTERS"] + i] = 0x77
    for i in range(6):
        mpu.memory[labels["ANIMATED_CHAR_TIMERS"] + i] = 0x55
        mpu.memory[labels["ANIMATED_CHAR_CUR_FRAME"] + i] = 0x44
        mpu.memory[labels["ANIMATED_CHAR_CUR_SEGMENT"] + i] = 0x33
        mpu.memory[labels["ANIMATED_CHAR_REPEAT_COUNTER"] + i] = 0x22

    run_subroutine(mpu, labels["INIT_CHARSET_ANIMATION"])

    # Rotated char counters reset to speeds
    for i in range(2):
        expected_speed = mpu.memory[labels["ANIM_CHAR_SPEEDS"] + i]
        assert mpu.memory[labels["ANIM_CHAR_COUNTERS"] + i] == expected_speed

    # Animated char states reset to initial values
    for i in range(6):
        assert mpu.memory[labels["ANIMATED_CHAR_TIMERS"] + i] == 1
        assert mpu.memory[labels["ANIMATED_CHAR_CUR_FRAME"] + i] == 255
        assert mpu.memory[labels["ANIMATED_CHAR_CUR_SEGMENT"] + i] == 0
        expected_repeat = mpu.memory[labels["ANIMATED_CHAR_INIT_REPEATS"] + i]
        assert mpu.memory[labels["ANIMATED_CHAR_REPEAT_COUNTER"] + i] == expected_repeat


def test_animate_charset_rotation_emulation(project_root: Path, labels: Dict[str, int]) -> None:
    """Verify animate_charset rotates 8 bytes 2 bits left in place and preserves PTR_SRC."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    ptr_src = labels["PTR_SRC"]
    mpu.memory[ptr_src] = 0x34
    mpu.memory[ptr_src + 1] = 0x12

    # Character index for rotated character 0 is 5: address $7400 + 5 * 8 = $7428
    char_addr = 0x7400 + 5 * 8
    # Test pattern: 0x81 (%10000001) rotated 2 bits left should become 0x06 (%00000110)
    test_bytes = [0x81, 0xAA, 0x55, 0xFF, 0x00, 0x40, 0x01, 0xC3]
    expected_rotated = [
        0x06,  # 10000001 -> 00000110
        0xAA,  # 10101010 -> 10101010
        0x55,  # 01010101 -> 01010101
        0xFF,  # 11111111 -> 11111111
        0x00,  # 00000000 -> 00000000
        0x01,  # 01000000 -> 00000001
        0x04,  # 00000001 -> 00000100
        0x0F,  # 11000011 -> 00001111
    ]
    for i, b in enumerate(test_bytes):
        mpu.memory[char_addr + i] = b

    # Force counter to 1 so the next call triggers rotation
    mpu.memory[labels["ANIM_CHAR_COUNTERS"]] = 1

    run_subroutine(mpu, labels["ANIMATE_CHARSET"])

    # Counter must be reset to speed
    speed = mpu.memory[labels["ANIM_CHAR_SPEEDS"]]
    assert mpu.memory[labels["ANIM_CHAR_COUNTERS"]] == speed

    # Bytes must match 2-bit left rotation
    for i in range(8):
        actual = mpu.memory[char_addr + i]
        assert actual == expected_rotated[i], f"Byte {i}: expected ${expected_rotated[i]:02X}, got ${actual:02X}"

    # Verify PTR_SRC was safely restored on stack
    assert mpu.memory[ptr_src] == 0x34
    assert mpu.memory[ptr_src + 1] == 0x12


def test_update_animated_charset_first_frame(project_root: Path, labels: Dict[str, int]) -> None:
    """Verify update_animated_charset loads first frame and preserves PTR_SRC/PTR_DST."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    ptr_src = labels["PTR_SRC"]
    ptr_dst = labels["PTR_DST"]
    mpu.memory[ptr_src] = 0xAA
    mpu.memory[ptr_src + 1] = 0x55
    mpu.memory[ptr_dst] = 0x11
    mpu.memory[ptr_dst + 1] = 0x22

    # Reset animation state
    run_subroutine(mpu, labels["INIT_CHARSET_ANIMATION"])

    # Timers are 1 after init, so next call triggers update for all 6 characters
    run_subroutine(mpu, labels["UPDATE_ANIMATED_CHARSET"])

    # Entry 0 is character 112: segment 0 has 1 frame, duration 100, data all 00
    char112_addr = 0x7400 + 112 * 8
    for i in range(8):
        assert mpu.memory[char112_addr + i] == 0

    assert mpu.memory[labels["ANIMATED_CHAR_CUR_FRAME"]] == 0
    assert mpu.memory[labels["ANIMATED_CHAR_TIMERS"]] == 100

    # Verify zero page preserved
    assert mpu.memory[ptr_src] == 0xAA
    assert mpu.memory[ptr_src + 1] == 0x55
    assert mpu.memory[ptr_dst] == 0x11
    assert mpu.memory[ptr_dst + 1] == 0x22


def test_update_animated_charset_segment_transition(project_root: Path, labels: Dict[str, int]) -> None:
    """Verify update_animated_charset transitions from segment 0 to segment 1."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    run_subroutine(mpu, labels["INIT_CHARSET_ANIMATION"])
    run_subroutine(mpu, labels["UPDATE_ANIMATED_CHARSET"])

    # Entry 0 (char 112): currently in Segment 0, Frame 0, Timer 100.
    # Force timer to 1 and run again -> finishes segment 0, advances to segment 1, frame 0
    mpu.memory[labels["ANIMATED_CHAR_TIMERS"]] = 1
    run_subroutine(mpu, labels["UPDATE_ANIMATED_CHARSET"])

    assert mpu.memory[labels["ANIMATED_CHAR_CUR_SEGMENT"]] == 1
    assert mpu.memory[labels["ANIMATED_CHAR_CUR_FRAME"]] == 0
    assert mpu.memory[labels["ANIMATED_CHAR_REPEAT_COUNTER"]] == 10
    assert mpu.memory[labels["ANIMATED_CHAR_TIMERS"]] == 5

    # Char 112 segment 1 frame 0 data: "00 3C C3 83 C3 00 3C 2C"
    char112_addr = 0x7400 + 112 * 8
    expected_f0 = [0x00, 0x3C, 0xC3, 0x83, 0xC3, 0x00, 0x3C, 0x2C]
    for i in range(8):
        assert mpu.memory[char112_addr + i] == expected_f0[i]
