"""Unit and py65 integration tests for secret object collision, score increment, run persistence, and new game restoration."""

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


def test_secret_metadata_and_bitmask(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that secret objects have bit 2 ($04) set in obj_type_flags and baked screens_blocking."""
    mpu = clean_mpu

    # Code 118 (Star / Gwiazdka) has secret: true
    flags_addr = labels["OBJ_TYPE_FLAGS"]
    assert mpu.memory[flags_addr + 118] & 0x04 == 0x04

    # Screen 0 (FOREST_01) has object 118 at packed_xy=145 -> (x=17*2=34, y=(145>>4)&0x0E = 8)
    blk_addr = labels["SCREEN_FOREST_01_BLOCKING"]
    # Row 8, col 34 in 40-col matrix: 8 * 40 + 34 = 354
    assert mpu.memory[blk_addr + 354] & 0x04 == 0x04

    # Total secret objects backup count
    total_secrets = mpu.memory[labels["SECRET_OBJS_TOTAL"]]
    assert total_secrets > 0


def test_add_score_1_bcd_increment(labels: Dict[str, int], clean_mpu: MPU):
    """Test add_score_1 increments 4-digit decimal SCORE and handles carry across units, tens, hundreds."""
    mpu = clean_mpu
    score_addr = labels["SCORE"]

    # Initial score: 0000 -> add 1 -> 0001
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 0])
    run_subroutine(mpu, labels["ADD_SCORE_1"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 0, 1]

    # Score: 0009 -> add 1 -> 0010
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 9])
    run_subroutine(mpu, labels["ADD_SCORE_1"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 1, 0]

    # Score: 0099 -> add 1 -> 0100
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 9, 9])
    run_subroutine(mpu, labels["ADD_SCORE_1"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 1, 0, 0]

    # Score: 0999 -> add 1 -> 1000
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 9, 9, 9])
    run_subroutine(mpu, labels["ADD_SCORE_1"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [1, 0, 0, 0]

    # Score: 9999 -> add 1 -> caps at 9999
    mpu.memory[score_addr : score_addr + 4] = bytearray([9, 9, 9, 9])
    run_subroutine(mpu, labels["ADD_SCORE_1"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [9, 9, 9, 9]


def test_secret_does_not_trigger_blocking_crash(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that an active secret flag ($04) in blocking_col8/9 does NOT cause dragon crash."""
    mpu = clean_mpu

    # Dragon at Y=100 (row 4..5)
    mpu.memory[labels["DRAGON_Y"]] = 100

    # Place ONLY secret mask ($04) in blocking_col8 and col9
    col8_addr = labels["BLOCKING_COL8"]
    col9_addr = labels["BLOCKING_COL9"]
    for i in range(11):
        mpu.memory[col8_addr + i] = 0x00
        mpu.memory[col9_addr + i] = 0x00
    mpu.memory[col8_addr + 4] = 0x04
    mpu.memory[col9_addr + 4] = 0x04

    # Run check_dragon_blocking_collision: Carry should be CLEAR (no crash)
    mpu.p |= 0x01  # Set carry initially
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0, "Secret object must NOT trigger blocking wall crash!"


def test_secret_collection_flow(labels: Dict[str, int], clean_mpu: MPU):
    """Test full collection of secret object:
    - Collision detected
    - Object erased from VRAM & blocking_col
    - SCORE incremented
    - Pickup chime sound triggered
    """
    mpu = clean_mpu

    # Screen 0 in left position, scrolled so col 34 aligns with col 8
    # Left screen col0 = 8 - incoming_col_idx -> col 34 at col 8 means 34 + (8 - incoming_col_idx) = 8
    # -> incoming_col_idx = 34
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 1
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = 34
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0

    # Dragon at row 8: scanline 34 + 8*16 = 162
    mpu.memory[labels["DRAGON_Y"]] = 162
    mpu.memory[labels["BLOCKING_COL8"] + 8] = 0x04

    # Initial score
    score_addr = labels["SCORE"]
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 0])

    # Set initial energy: block 20, sub-step 86
    counter_full = labels["COUNTER_FULL"]
    counter_eight = labels["COUNTER_EIGHT"]
    mpu.memory[counter_full] = 20
    mpu.memory[counter_eight] = 86
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["GAME_OVER_REASON"]] = 0

    # Pre-render a non-zero tile in GAME_ACTION_VRAM at row 8, col 8
    action_vram = labels["GAME_ACTION_VRAM"]
    mpu.memory[action_vram + 8 * 48 + 8] = 0x49

    # Run check_dragon_secret_collision
    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Verify Carry SET
    assert (mpu.p & 0x01) == 0x01, "check_dragon_secret_collision should return Carry SET"

    # Score should now be 0001
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 0, 1]

    # Energy should be increased by 10 sub-steps: COUNTER_FULL=21, COUNTER_EIGHT=84
    assert mpu.memory[counter_full] == 21
    assert mpu.memory[counter_eight] == 84

    # Secret click sound timer triggered
    assert mpu.memory[labels["SECRET_SOUND_TIMER"]] == labels.get("SECRET_CLICK_FRAMES", 3)

    # Tile in GAME_ACTION_VRAM should be erased to 0
    assert mpu.memory[action_vram + 8 * 48 + 8] == 0x00

    # Collision in blocking_col8 should be cleared
    assert mpu.memory[labels["BLOCKING_COL8"] + 8] == 0x00


def test_secret_run_persistence_and_game_init_restoration(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that collected secret stays erased across respawns, but restores on game_init."""
    mpu = clean_mpu

    # Check initial tile and blocking mask for Screen 0 at row 8, col 34
    blk_addr = labels["SCREEN_FOREST_01_BLOCKING"]
    vram_addr = labels["SCREEN_FOREST_01_VRAM"]
    offset = 8 * 40 + 34
    orig_blk = mpu.memory[blk_addr + offset]
    orig_tile = mpu.memory[vram_addr + offset]
    assert orig_blk & 0x04 == 0x04
    assert orig_tile != 0

    # Collect secret via collision routine
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 1
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = 34
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0
    mpu.memory[labels["DRAGON_Y"]] = 162
    mpu.memory[labels["BLOCKING_COL8"] + 8] = 0x04

    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Check that source buffers were cleared for this secret!
    assert mpu.memory[blk_addr + offset] == 0x00
    assert mpu.memory[vram_addr + offset] == 0x00

    # Simulate dragon respawn: respawn_dragon calls init_flame_collision
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])
    # Secret must STILL BE ERASED in source buffers!
    assert mpu.memory[blk_addr + offset] == 0x00
    assert mpu.memory[vram_addr + offset] == 0x00

    # Now simulate brand new game: call game_init (stubbing show_level_name_screen with RTS)
    mpu.memory[labels["SHOW_LEVEL_NAME_SCREEN"]] = 0x60
    run_subroutine(mpu, labels["GAME_INIT"])

    # Secret must now be RESTORED to original tile and mask in source buffers...
    assert mpu.memory[blk_addr + offset] == orig_blk
    assert mpu.memory[vram_addr + offset] == orig_tile

    # ...AND loaded into active GAME_ACTION_VRAM when level 1 screens are loaded (col 4 + 34 = 38)!
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 1
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    action_vram = labels["GAME_ACTION_VRAM"]
    assert mpu.memory[action_vram + 8 * 48 + 38] == orig_tile


def test_add_score_5_bcd_increment(labels: Dict[str, int], clean_mpu: MPU):
    """Test add_score_5 increments 4-digit decimal SCORE by 5 with BCD carry."""
    mpu = clean_mpu
    score_addr = labels["SCORE"]

    # Initial score: 0000 -> add 5 -> 0005
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 0])
    run_subroutine(mpu, labels["ADD_SCORE_5"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 0, 5]

    # Score: 0007 -> add 5 -> 0012
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 7])
    run_subroutine(mpu, labels["ADD_SCORE_5"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 1, 2]

    # Score: 0098 -> add 5 -> 0103
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 9, 8])
    run_subroutine(mpu, labels["ADD_SCORE_5"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 1, 0, 3]

    # Score: 0995 -> add 5 -> 1000
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 9, 9, 5])
    run_subroutine(mpu, labels["ADD_SCORE_5"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [1, 0, 0, 0]

    # Score: 9998 -> add 5 -> caps at 9999
    mpu.memory[score_addr : score_addr + 4] = bytearray([9, 9, 9, 8])
    run_subroutine(mpu, labels["ADD_SCORE_5"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [9, 9, 9, 9]


def test_add_score_10_bcd_increment(labels: Dict[str, int], clean_mpu: MPU):
    """Test add_score_10 increments 4-digit decimal SCORE by 10 with BCD carry."""
    mpu = clean_mpu
    score_addr = labels["SCORE"]

    # Initial score: 0005 -> add 10 -> 0015
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 5])
    run_subroutine(mpu, labels["ADD_SCORE_10"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 1, 5]

    # Score: 0095 -> add 10 -> 0105
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 9, 5])
    run_subroutine(mpu, labels["ADD_SCORE_10"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 1, 0, 5]

    # Score: 0995 -> add 10 -> 1005
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 9, 9, 5])
    run_subroutine(mpu, labels["ADD_SCORE_10"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [1, 0, 0, 5]

    # Score: 9995 -> add 10 -> caps at 9999
    mpu.memory[score_addr : score_addr + 4] = bytearray([9, 9, 9, 5])
    run_subroutine(mpu, labels["ADD_SCORE_10"])
    assert list(mpu.memory[score_addr : score_addr + 4]) == [9, 9, 9, 9]


def test_add_shot_1(labels: Dict[str, int], clean_mpu: MPU):
    """Test add_shot_1 increments SHOTS and caps at 99."""
    mpu = clean_mpu
    shots_addr = labels["SHOTS"]

    mpu.memory[shots_addr] = 1
    run_subroutine(mpu, labels["ADD_SHOT_1"])
    assert mpu.memory[shots_addr] == 2

    mpu.memory[shots_addr] = 99
    run_subroutine(mpu, labels["ADD_SHOT_1"])
    assert mpu.memory[shots_addr] == 99


def test_increase_energy_100(labels: Dict[str, int], clean_mpu: MPU):
    """Test increase_energy_100 advances energy by 100 sub-steps across blocks."""
    mpu = clean_mpu
    counter_full = labels["COUNTER_FULL"]
    counter_eight = labels["COUNTER_EIGHT"]

    # Start with COUNTER_FULL = 20, COUNTER_EIGHT = 86
    mpu.memory[counter_full] = 20
    mpu.memory[counter_eight] = 86
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["GAME_OVER_REASON"]] = 0

    run_subroutine(mpu, labels["INCREASE_ENERGY_100"])
    # 100 steps from (20, 86):
    # 4 steps to finish block 20 -> block 21 at 90 (96 steps remaining)
    # 96 / 8 = 12 full blocks -> block 21 + 12 = block 33 at 90
    assert mpu.memory[counter_full] == 33
    assert mpu.memory[counter_eight] == 90


def test_interactive_does_not_trigger_blocking_crash(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that interactive ($02) and secret+interactive ($06) do NOT cause dragon crash."""
    mpu = clean_mpu

    mpu.memory[labels["DRAGON_Y"]] = 100
    col8_addr = labels["BLOCKING_COL8"]
    col9_addr = labels["BLOCKING_COL9"]
    for i in range(11):
        mpu.memory[col8_addr + i] = 0x00
        mpu.memory[col9_addr + i] = 0x00

    # Test interactive flag ($02)
    mpu.memory[col8_addr + 4] = 0x02
    mpu.p |= 0x01
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0, "Interactive flag ($02) must NOT trigger blocking wall crash!"

    # Test both flags ($06)
    mpu.memory[col8_addr + 4] = 0x06
    mpu.p |= 0x01
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0, "Secret+Interactive flag ($06) must NOT trigger blocking wall crash!"


def test_interactive_collection_flow(labels: Dict[str, int], clean_mpu: MPU):
    """Test collection of object with interactive flag ($02):
    - SCORE + 5
    - Energy + 100 units
    - Object erased from VRAM & blocking_col
    - Pickup sound triggered
    """
    mpu = clean_mpu

    # Configure object 118 with ONLY interactive flag ($02)
    flags_addr = labels["OBJ_TYPE_FLAGS"]
    mpu.memory[flags_addr + 118] = 0x02

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 1
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = 34
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0

    mpu.memory[labels["DRAGON_Y"]] = 162
    mpu.memory[labels["BLOCKING_COL8"] + 8] = 0x02

    # Set initial score to 0000, initial lives to 3
    score_addr = labels["SCORE"]
    lives_addr = labels["LIVES"]
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 0])
    mpu.memory[lives_addr] = 3

    # Set initial energy: block 20, sub-step 86
    counter_full = labels["COUNTER_FULL"]
    counter_eight = labels["COUNTER_EIGHT"]
    mpu.memory[counter_full] = 20
    mpu.memory[counter_eight] = 86
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["GAME_OVER_REASON"]] = 0

    # Action VRAM non-zero tile
    action_vram = labels["GAME_ACTION_VRAM"]
    mpu.memory[action_vram + 8 * 48 + 8] = 0x49

    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Verify Carry SET
    assert (mpu.p & 0x01) == 0x01

    # SCORE should be 0005 (+5)
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 0, 5]

    # Energy should be increased by 40 sub-steps: COUNTER_FULL=25, COUNTER_EIGHT=86
    assert mpu.memory[counter_full] == 25
    assert mpu.memory[counter_eight] == 86

    # LIVES should be incremented to 4 (+1)
    assert mpu.memory[lives_addr] == 4

    # Pickup sound triggered
    assert mpu.memory[labels["SECRET_SOUND_TIMER"]] == labels.get("SECRET_CLICK_FRAMES", 3)

    # Erased from VRAM & blocking_col
    assert mpu.memory[action_vram + 8 * 48 + 8] == 0x00
    assert mpu.memory[labels["BLOCKING_COL8"] + 8] == 0x00


def test_secret_and_interactive_collection_flow(labels: Dict[str, int], clean_mpu: MPU):
    """Test collection of object with BOTH secret and interactive flags ($06):
    - SCORE + 10
    - SHOTS + 1
    - Object erased from VRAM & blocking_col
    - Pickup sound triggered
    """
    mpu = clean_mpu

    # Configure object 118 with BOTH flags ($06)
    flags_addr = labels["OBJ_TYPE_FLAGS"]
    mpu.memory[flags_addr + 118] = 0x06

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 1
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = 34
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0

    mpu.memory[labels["DRAGON_Y"]] = 162
    mpu.memory[labels["BLOCKING_COL8"] + 8] = 0x06

    # Set initial score to 0000, initial shots to 1
    score_addr = labels["SCORE"]
    shots_addr = labels["SHOTS"]
    mpu.memory[score_addr : score_addr + 4] = bytearray([0, 0, 0, 0])
    mpu.memory[shots_addr] = 1

    # Set initial energy: block 20, sub-step 86
    counter_full = labels["COUNTER_FULL"]
    counter_eight = labels["COUNTER_EIGHT"]
    mpu.memory[counter_full] = 20
    mpu.memory[counter_eight] = 86
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["GAME_OVER_REASON"]] = 0

    # Action VRAM non-zero tile
    action_vram = labels["GAME_ACTION_VRAM"]
    mpu.memory[action_vram + 8 * 48 + 8] = 0x49

    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Verify Carry SET
    assert (mpu.p & 0x01) == 0x01

    # SCORE should be 0010 (+10)
    assert list(mpu.memory[score_addr : score_addr + 4]) == [0, 0, 1, 0]

    # Energy should be increased by 80 sub-steps: COUNTER_FULL=30, COUNTER_EIGHT=86
    assert mpu.memory[counter_full] == 30
    assert mpu.memory[counter_eight] == 86

    # SHOTS should be incremented to 2
    assert mpu.memory[shots_addr] == 2

    # Pickup sound triggered
    assert mpu.memory[labels["SECRET_SOUND_TIMER"]] == labels.get("SECRET_CLICK_FRAMES", 3)

    # Erased from VRAM & blocking_col
    assert mpu.memory[action_vram + 8 * 48 + 8] == 0x00
    assert mpu.memory[labels["BLOCKING_COL8"] + 8] == 0x00


def test_dragon_frame_dependent_collision_bounds(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that collision routines use per-frame vertical pixel bounds (min_y, max_y):
    - In frame 3 (folded wings, lines 8..18), dragon at y=74 does not reach row 4, avoiding obstacle.
    - In frame 7 (wings fully spread, lines 0..25), dragon at y=74 reaches row 4, triggering crash.
    """
    mpu = clean_mpu

    # Place an obstacle only at row 4 in blocking_col8
    for r in range(11):
        mpu.memory[labels["BLOCKING_COL8"] + r] = 0x00
        mpu.memory[labels["BLOCKING_COL9"] + r] = 0x00
    mpu.memory[labels["BLOCKING_COL8"] + 4] = 0x01

    mpu.memory[labels["DRAGON_Y"]] = 74

    # Frame 3: folded wings (lines 8..18)
    # y=74: rel_end = 74 + 18 - 34 = 58 -> row 3. Row 4 is NOT included!
    mpu.memory[labels["ANIM_PHASE"] + 1] = 3
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0, "Frame 3 with folded wings should pass over row 4 obstacle without collision"

    # Frame 7: fully spread wings (lines 0..25)
    # y=74: rel_end = 74 + 25 - 34 = 65 -> row 4. Row 4 IS included!
    mpu.memory[labels["ANIM_PHASE"] + 1] = 7
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 1, "Frame 7 with spread wings should collide with row 4 obstacle"
