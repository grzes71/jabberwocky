"""Unit and py65 integration tests for dragon fire collision and object destruction."""

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


@pytest.fixture
def clean_mpu(project_root: Path) -> MPU:
    xex_file = project_root / "jabberwocky.xex"
    assert xex_file.exists(), "jabberwocky.xex must exist (run make all)"
    mem = bytearray(65536)
    load_xex(xex_file, mem)
    mpu = MPU(memory=mem)
    return mpu


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


def test_flame_collision_symbols_exist(labels: Dict[str, int]):
    """Verify that all flame collision and destruction symbols exist."""
    expected = [
        "CHECK_FLAME_OBJECT_COLLISION",
        "INIT_FLAME_COLLISION",
        "FLAME_M_PF",
        "SCREEN_OBJ_DESTROYED",
        "ERASE_CUR_OBJECT",
        "FLAME_COL_MIN",
        "FLAME_COL_MAX_TBL",
        "VRAM_ROW_OFFSETS_LO",
        "VRAM_ROW_OFFSETS_HI",
        "BLOCKING_COL8",
        "BLOCKING_COL9",
        "INIT_BLOCKING_COLS",
        "SHIFT_BLOCKING_COLS",
        "CHECK_DRAGON_BLOCKING_COLLISION",
    ]
    for sym in expected:
        assert sym in labels, f"Missing symbol: {sym}"


def test_flame_inactive_early_exit(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify check_flame_object_collision exits early when fire_state == 0."""
    mpu = clean_mpu
    vram_base = labels["GAME_ACTION_VRAM"]
    mpu.memory[labels["FIRE_STATE"]] = 0
    mpu.memory[labels["FLAME_M_PF"]] = 0x0F  # Non-zero latch

    # Mark a marker in VRAM
    mpu.memory[vram_base + 50] = 0x42

    run_subroutine(mpu, labels["CHECK_FLAME_OBJECT_COLLISION"])

    # Latch should be cleared, and VRAM untouched
    assert mpu.memory[labels["FLAME_M_PF"]] == 0
    assert mpu.memory[vram_base + 50] == 0x42


def test_flame_no_hardware_hit_early_exit(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify check_flame_object_collision exits early when flame_m_pf == 0."""
    mpu = clean_mpu
    vram_base = labels["GAME_ACTION_VRAM"]
    mpu.memory[labels["FIRE_STATE"]] = 1
    mpu.memory[labels["FLAME_M_PF"]] = 0  # No hardware playfield collision

    mpu.memory[vram_base + 50] = 0x42

    run_subroutine(mpu, labels["CHECK_FLAME_OBJECT_COLLISION"])

    # Marker must be unchanged
    assert mpu.memory[vram_base + 50] == 0x42


def test_flame_destroys_object_in_path(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify an object in the line of fire is destroyed and erased from VRAM."""
    mpu = clean_mpu
    vram_base = labels["GAME_ACTION_VRAM"]

    # 1. Initialize level 0 screens (screen 0 loaded into cols 4..43)
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Object 23 on Screen 0 (code 48) is at x=10, y=8, size 2x1.
    # In VRAM: cols = 4 + 10 = 14..15, row = 8.
    cell_r8_c14 = vram_base + 8 * 48 + 14
    cell_r8_c15 = vram_base + 8 * 48 + 15

    # Verify cells contain object tiles initially ($47, $48)
    assert mpu.memory[cell_r8_c14] != 0, "Object cell should have baked tiles initially"
    assert mpu.memory[cell_r8_c15] != 0

    # Ensure object 48 is marked as blocking=true (bit 0 = 1)
    flags_base = labels["OBJ_TYPE_FLAGS"]
    mpu.memory[flags_base + 48] = 0x01

    # 2. Position dragon facing row 8: dragon_y = 155
    # (rel_start = 155 - 24 = 131, row = 131 // 16 = 8)
    mpu.memory[labels["DRAGON_Y"]] = 155
    mpu.memory[labels["FIRE_STATE"]] = 2     # PEAK HOLD
    mpu.memory[labels["FIRE_FRAME"]] = 7     # Full reach (cols 10..18)
    mpu.memory[labels["FLAME_M_PF"]] = 0x01   # Hardware collision with PF0

    # Bit 23 of screen 0: index 23 // 8 = byte 2, bit 23 % 8 = 7 (mask 0x80)
    destroyed_base = labels["SCREEN_OBJ_DESTROYED"]
    assert (mpu.memory[destroyed_base + 2] & 0x80) == 0, "Object 23 should not be destroyed yet"

    # 3. Trigger collision check
    run_subroutine(mpu, labels["CHECK_FLAME_OBJECT_COLLISION"])

    # 4. Verify all object cells are erased to $00 (background)
    assert mpu.memory[cell_r8_c14] == 0, "Cell (r8, c14) must be cleared"
    assert mpu.memory[cell_r8_c15] == 0, "Cell (r8, c15) must be cleared"

    # 5. Verify destroyed bitmask is set
    assert (mpu.memory[destroyed_base + 2] & 0x80) != 0, "Bit for object 23 must be set"

    # 6. Verify hardware latch was cleared
    assert mpu.memory[labels["FLAME_M_PF"]] == 0


def test_flame_different_row_does_not_destroy_object(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify an object on a different row than the flame is NOT destroyed."""
    mpu = clean_mpu
    vram_base = labels["GAME_ACTION_VRAM"]

    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Object 23 is on row 8
    cell_r8_c14 = vram_base + 8 * 48 + 14
    initial_tile = mpu.memory[cell_r8_c14]
    assert initial_tile != 0

    # Dragon on row 2 (dragon_y = 60: rel_start = 36 // 16 = row 2)
    mpu.memory[labels["DRAGON_Y"]] = 60
    mpu.memory[labels["FIRE_STATE"]] = 1
    mpu.memory[labels["FIRE_FRAME"]] = 4
    mpu.memory[labels["FLAME_M_PF"]] = 0x02

    run_subroutine(mpu, labels["CHECK_FLAME_OBJECT_COLLISION"])

    # Object on row 8 must be intact
    assert mpu.memory[cell_r8_c14] == initial_tile

    destroyed_base = labels["SCREEN_OBJ_DESTROYED"]
    assert (mpu.memory[destroyed_base + 2] & 0x80) == 0, "Object 23 bit must not be set"


def test_flame_destroyed_object_not_reprocessed(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify an object marked as destroyed is skipped on subsequent collision checks."""
    mpu = clean_mpu
    vram_base = labels["GAME_ACTION_VRAM"]

    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Pre-mark object 23 as destroyed (byte 2, bit 7 of screen 0)
    destroyed_base = labels["SCREEN_OBJ_DESTROYED"]
    mpu.memory[destroyed_base + 2] |= 0x80

    # Write a test value into the object's cell
    cell_r8_c14 = vram_base + 8 * 48 + 14
    mpu.memory[cell_r8_c14] = 0xAA

    # Aim dragon right at it
    mpu.memory[labels["DRAGON_Y"]] = 155
    mpu.memory[labels["FIRE_STATE"]] = 2
    mpu.memory[labels["FIRE_FRAME"]] = 7
    mpu.memory[labels["FLAME_M_PF"]] = 0x01

    run_subroutine(mpu, labels["CHECK_FLAME_OBJECT_COLLISION"])

    # Cell must NOT be erased (remains 0xAA) because object was skipped
    assert mpu.memory[cell_r8_c14] == 0xAA


def test_flame_non_blocking_object_not_destroyed(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that objects with blocking=False (bit 0 == 0) are NOT destroyed by flame."""
    mpu = clean_mpu
    vram_base = labels["GAME_ACTION_VRAM"]

    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Object 23 is code 48 on row 8, col 14
    cell_r8_c14 = vram_base + 8 * 48 + 14
    initial_tile = mpu.memory[cell_r8_c14]
    assert initial_tile != 0

    # Set object 48 flags to 0 (non-blocking)
    flags_base = labels["OBJ_TYPE_FLAGS"]
    mpu.memory[flags_base + 48] = 0x00

    # Aim dragon right at it with active fire and hit
    mpu.memory[labels["DRAGON_Y"]] = 155
    mpu.memory[labels["FIRE_STATE"]] = 2
    mpu.memory[labels["FIRE_FRAME"]] = 7
    mpu.memory[labels["FLAME_M_PF"]] = 0x01

    run_subroutine(mpu, labels["CHECK_FLAME_OBJECT_COLLISION"])

    # Object must NOT be destroyed because blocking=false!
    assert mpu.memory[cell_r8_c14] == initial_tile, "Non-blocking object must not be erased from VRAM"

    destroyed_base = labels["SCREEN_OBJ_DESTROYED"]
    assert (mpu.memory[destroyed_base + 2] & 0x80) == 0, "Non-blocking object bit must not be set"


def test_dragon_crash_on_blocking_object(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that colliding with playfield triggers crash when object has blocking=true."""
    mpu = clean_mpu
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Dragon at row 0 (y=40) overlapping Object 12 (code 51, cols 8..9, rows 0..1)
    mpu.memory[labels["DRAGON_Y"]] = 40
    mpu.memory[labels["OBJ_TYPE_FLAGS"] + 51] = 0x01  # blocking = true
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["DRAGON_P0PF"]] = 0x01          # PF0 collision

    run_subroutine(mpu, labels["CHECK_DRAGON_COLLISIONS"])

    # Dragon MUST enter crash state (3)
    assert mpu.memory[labels["DRAGON_DYING"]] == 3


def test_dragon_no_crash_on_non_blocking_object(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that colliding with playfield does NOT trigger crash when object has blocking=false (cell is 0)."""
    mpu = clean_mpu
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Clear cells under dragon in blocking_col8 and blocking_col9 (rows 0..1) simulating non-blocking decor
    col8_base = labels["BLOCKING_COL8"]
    col9_base = labels["BLOCKING_COL9"]
    for r in range(11):
        mpu.memory[col8_base + r] = 0
        mpu.memory[col9_base + r] = 0

    # Dragon at row 0 (y=40)
    mpu.memory[labels["DRAGON_Y"]] = 40
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["DRAGON_P0PF"]] = 0x01          # PF0 collision with non-blocking decor

    run_subroutine(mpu, labels["CHECK_DRAGON_COLLISIONS"])

    # Dragon must NOT crash! (remains 0, alive)
    assert mpu.memory[labels["DRAGON_DYING"]] == 0


def test_dragon_no_crash_on_destroyed_blocking_object(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that a blocking object destroyed by flame does NOT cause crash."""
    mpu = clean_mpu
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Object at row 1, cols 8..9 is initially blocking
    col8_base = labels["BLOCKING_COL8"]
    col9_base = labels["BLOCKING_COL9"]
    assert mpu.memory[col8_base + 1] == 1
    assert mpu.memory[col9_base + 1] == 1

    # Destroy/erase object using ERASE_CUR_OBJECT
    mpu.memory[labels["FC_CUR_OBJ_Y"]] = 0
    mpu.memory[labels["FC_CUR_VRAM_X"]] = 8
    mpu.memory[labels["FC_CUR_OBJ_W"]] = 2
    mpu.memory[labels["FC_CUR_OBJ_H"]] = 2
    run_subroutine(mpu, labels["ERASE_CUR_OBJECT"])

    # Verify both VRAM and blocking columns were erased to 0
    assert mpu.memory[col8_base + 1] == 0
    assert mpu.memory[col9_base + 1] == 0

    # Dragon touches PF pixel at this location
    mpu.memory[labels["DRAGON_Y"]] = 40
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["DRAGON_P0PF"]] = 0x01

    run_subroutine(mpu, labels["CHECK_DRAGON_COLLISIONS"])

    # Destroyed object must not trigger crash!
    assert mpu.memory[labels["DRAGON_DYING"]] == 0



