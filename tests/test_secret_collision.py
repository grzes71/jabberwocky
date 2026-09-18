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


def get_forest_level_idx(project_root: Path) -> int:
    import yaml
    with open(project_root / "world" / "project.yaml", "r", encoding="utf-8") as f:
        proj = yaml.safe_load(f)
    for idx, lab in enumerate(proj.get("labyrinths", [])):
        if "FOREST_01" in lab.get("screens", []):
            return idx
    return 0


def find_secret_on_screen0(project_root: Path):
    import yaml
    with open(project_root / "world" / "project.yaml", "r", encoding="utf-8") as f:
        proj = yaml.safe_load(f)
    with open(project_root / "world" / "objects.yaml", "r", encoding="utf-8") as f:
        objs_data = yaml.safe_load(f)
    objs_list = objs_data.get("objects", []) if isinstance(objs_data, dict) else objs_data
    secret_codes = {
        o["code"] for o in objs_list
        if isinstance(o, dict) and o.get("flags", {}).get("secret", False)
    }
    screen_map = {s["id"]: s for s in proj.get("screens", [])}
    for level_idx, lab in enumerate(proj.get("labyrinths", [])):
        screens = lab.get("screens", [])
        if not screens:
            continue
        s0_id = screens[0]
        s0 = screen_map.get(s0_id, {})
        for obj in s0.get("objects", []):
            if obj.get("code") in secret_codes:
                obj_def = next(d for d in objs_list if d.get("code") == obj.get("code"))
                tiles = obj_def.get("tiles", [])
                w = obj_def.get("size", {}).get("width", 1)
                for idx_tile, t in enumerate(tiles):
                    if t != 0:
                        dx = idx_tile % w
                        dy = idx_tile // w
                        pxy = obj.get("packed_xy", 0)
                        x = (pxy & 0x0F) * 2 + dx
                        y = ((pxy >> 4) & 0x0E) + dy
                        return level_idx, obj.get("code"), x, y
    raise RuntimeError("No secret object found on screen 0 of any labyrinth in project.yaml")


def test_secret_metadata_and_bitmask(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Verify that secret objects have bit 2 ($04) set in obj_type_flags and baked screens_blocking."""
    mpu = clean_mpu

    # Code 118 (Star / Gwiazdka) has secret: true
    flags_addr = labels["OBJ_TYPE_FLAGS"]
    assert mpu.memory[flags_addr + 118] & 0x04 == 0x04

    level_idx, code, x, y = find_secret_on_screen0(project_root)
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    blk_addr = labels["SCREEN_BUF_A_BLK"]
    offset = y * 40 + x
    assert mpu.memory[blk_addr + offset] & 0x04 == 0x04


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


def test_secret_collection_flow(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Test full collection of secret object:
    - Collision detected
    - Object erased from VRAM & blocking_col
    - SCORE incremented
    - Pickup chime sound triggered
    """
    mpu = clean_mpu

    level_idx, code, x, y = find_secret_on_screen0(project_root)
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = x
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0

    # Dragon at row y: scanline 34 + y * 16
    mpu.memory[labels["DRAGON_Y"]] = 34 + y * 16
    mpu.memory[labels["BLOCKING_COL8"] + y] = 0x04

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

    # Pre-render a non-zero tile in GAME_ACTION_VRAM at row y, col 8
    action_vram = labels["GAME_ACTION_VRAM"]
    mpu.memory[action_vram + y * 48 + 8] = 0x49

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
    assert mpu.memory[action_vram + y * 48 + 8] == 0x00

    # Collision in blocking_col8 should be cleared
    assert mpu.memory[labels["BLOCKING_COL8"] + y] == 0x00


def test_secret_run_persistence_and_game_init_restoration(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Verify that collected secret stays erased across respawns, but restores on game_init."""
    mpu = clean_mpu

    level_idx, code, x, y = find_secret_on_screen0(project_root)
    # Initialize level screens to bake Screen 0 into Buffer A
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Check initial tile and blocking mask for Screen 0 at row y, col x
    blk_addr = labels["SCREEN_BUF_A_BLK"]
    vram_addr = labels["SCREEN_BUF_A_VRAM"]
    offset = y * 40 + x
    orig_blk = mpu.memory[blk_addr + offset]
    orig_tile = mpu.memory[vram_addr + offset]
    assert orig_blk & 0x04 == 0x04
    assert orig_tile != 0

    # Collect secret via collision routine
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = x
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0
    mpu.memory[labels["DRAGON_Y"]] = 34 + y * 16
    mpu.memory[labels["BLOCKING_COL8"] + y] = 0x04

    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Check that source buffers were cleared for this secret!
    assert mpu.memory[blk_addr + offset] == 0x00
    assert mpu.memory[vram_addr + offset] == 0x00

    # Simulate dragon respawn: respawn_dragon restarts level and re-bakes screen 0
    mpu.memory[labels["SHOW_LEVEL_NAME_SCREEN"]] = 0x60
    run_subroutine(mpu, labels["RESPAWN_DRAGON"])
    # Secret must STILL BE ERASED in source buffers and active VRAM!
    assert mpu.memory[blk_addr + offset] == 0x00
    assert mpu.memory[vram_addr + offset] == 0x00
    action_vram = labels["GAME_ACTION_VRAM"]
    vram_col = 4 + x
    assert mpu.memory[action_vram + y * 48 + vram_col] == 0x00

    # Now simulate brand new game: call game_init (stubbing show_level_name_screen with RTS)
    mpu.memory[labels["SHOW_LEVEL_NAME_SCREEN"]] = 0x60
    run_subroutine(mpu, labels["GAME_INIT"])

    # Load level screens to bake Screen 0 into staging buffer A
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Secret must now be RESTORED to original tile and mask in staging buffers...
    assert mpu.memory[blk_addr + offset] == orig_blk
    assert mpu.memory[vram_addr + offset] == orig_tile

    # ...AND loaded into active GAME_ACTION_VRAM when level screens are loaded (col 4 + x)!
    action_vram = labels["GAME_ACTION_VRAM"]
    assert mpu.memory[action_vram + y * 48 + vram_col] == orig_tile


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


def test_interactive_collection_flow(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Test collection of object with interactive flag ($02):
    - SCORE + 5
    - Energy + 100 units
    - Object erased from VRAM & blocking_col
    - Pickup sound triggered
    """
    mpu = clean_mpu

    level_idx, code, x, y = find_secret_on_screen0(project_root)
    # Configure object with ONLY interactive flag ($02)
    flags_addr = labels["OBJ_TYPE_FLAGS"]
    mpu.memory[flags_addr + code] = 0x02

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = x
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0

    mpu.memory[labels["DRAGON_Y"]] = 34 + y * 16
    mpu.memory[labels["BLOCKING_COL8"] + y] = 0x02

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
    mpu.memory[action_vram + y * 48 + 8] = 0x49

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
    assert mpu.memory[action_vram + y * 48 + 8] == 0x00
    assert mpu.memory[labels["BLOCKING_COL8"] + y] == 0x00


def test_secret_and_interactive_collection_flow(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Test collection of object with BOTH secret and interactive flags ($06):
    - SCORE + 10
    - SHOTS + 1
    - Object erased from VRAM & blocking_col
    - Pickup sound triggered
    """
    mpu = clean_mpu

    level_idx, code, x, y = find_secret_on_screen0(project_root)
    # Configure object with BOTH flags ($06)
    flags_addr = labels["OBJ_TYPE_FLAGS"]
    mpu.memory[flags_addr + code] = 0x06

    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = level_idx
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = x
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0

    mpu.memory[labels["DRAGON_Y"]] = 34 + y * 16
    mpu.memory[labels["BLOCKING_COL8"] + y] = 0x06

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
    mpu.memory[action_vram + y * 48 + 8] = 0x49

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
    assert mpu.memory[action_vram + y * 48 + 8] == 0x00
    assert mpu.memory[labels["BLOCKING_COL8"] + y] == 0x00


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


def test_obj_type_flags_has_empty_bit(labels: Dict[str, int], clean_mpu: MPU):
    """Verify bit 7 ($80) is set for objects with tile 0, and clear for 100% solid objects."""
    mpu = clean_mpu
    flags_base = labels["OBJ_TYPE_FLAGS"]

    # Code 31 (BARREL_2_2) has tiles: [0, 0, 100, 228] -> has tile 0!
    assert (mpu.memory[flags_base + 31] & 0x80) == 0x80

    # Code 154 (PYRAMID_BIG) has empty corners -> has tile 0!
    assert (mpu.memory[flags_base + 154] & 0x80) == 0x80

    # Code 118 (Star) has tiles: [118] -> 100% solid, NO tile 0!
    assert (mpu.memory[flags_base + 118] & 0x80) == 0x00


def test_secret_empty_glyph_ignored_by_collision(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Verify that collision with empty/transparent glyphs (tile == 0) inside object bounding box
    is ignored, while collision with solid glyphs (tile != 0) is collected.
    """
    mpu = clean_mpu

    # BARREL_2_2 is code 31: width=2, height=2.
    # Row 0: tiles [0, 0] (empty glyphs!)
    # Row 1: tiles [100, 228] (solid glyphs!)
    # Screen 0 objects: set object 0 to BARREL_2_2 at x=8, y=2
    # packed_xy = (y << 4) | (x >> 1) = (2 << 4) | 4 = $24
    screen0_codes = labels["SCREEN_FOREST_01_CODES"]
    screen0_coords = labels["SCREEN_FOREST_01_COORDS"]
    mpu.memory[screen0_codes] = 31
    mpu.memory[screen0_coords] = 0x24  # x=8, y=2

    # Level screen position 1, incoming_col_idx = 8 -> screen 0 is Left Screen at col0 = 8 - 8 = 0
    # Object at x=8 aligns with VRAM col 0 + 8 = 8!
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1
    mpu.memory[labels["INCOMING_COL_IDX"]] = 8
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = get_forest_level_idx(project_root)

    # Clear destroyed bitmask
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # CASE 1: Dragon at row 2 (which is row 0 of BARREL_2_2, tiles are 0, 0).
    # scanline = 34 + 2 * 16 = 66
    mpu.memory[labels["DRAGON_Y"]] = 66
    mpu.memory[labels["ANIM_PHASE"] + 1] = 0  # Frame 0: lines 2..22 (stays within row 2)

    # Put secret collision flag in blocking_col8 for row 2
    for r in range(11):
        mpu.memory[labels["BLOCKING_COL8"] + r] = 0x00
        mpu.memory[labels["BLOCKING_COL9"] + r] = 0x00
    mpu.memory[labels["BLOCKING_COL8"] + 2] = 0x04

    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Must NOT collect barrel because tile at (x=8, y=2) is 0!
    # Carry must be CLEAR (or no object collected)
    destroyed_mask = labels["SCREEN_OBJ_DESTROYED"]
    assert (mpu.memory[destroyed_mask] & 0x01) == 0, "Empty glyph (tile 0) must NOT trigger object collection!"

    # CASE 2: Dragon at row 3 (which is row 1 of BARREL_2_2, tiles are 100, 228 != 0).
    # scanline = 34 + 3 * 16 = 82
    mpu.memory[labels["DRAGON_Y"]] = 82
    mpu.memory[labels["ANIM_PHASE"] + 1] = 0

    # Put secret collision flag in blocking_col8 for row 3
    for r in range(11):
        mpu.memory[labels["BLOCKING_COL8"] + r] = 0x00
        mpu.memory[labels["BLOCKING_COL9"] + r] = 0x00
    mpu.memory[labels["BLOCKING_COL8"] + 3] = 0x04

    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Now it MUST collect the barrel because tile at (x=8, y=3) is 100 != 0!
    assert (mpu.memory[destroyed_mask] & 0x01) == 1, "Solid glyph (tile != 0) MUST trigger object collection!"


def test_init_flame_collision_clears_all_256_bytes(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that init_flame_collision clears all 256 bytes of screen_obj_destroyed."""
    mpu = clean_mpu
    destroyed_base = labels["SCREEN_OBJ_DESTROYED"]

    # Fill all 256 bytes with dirty 0xFF
    for i in range(256):
        mpu.memory[destroyed_base + i] = 0xFF

    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    for i in range(256):
        assert mpu.memory[destroyed_base + i] == 0x00, f"Byte {i} of screen_obj_destroyed must be 0x00 after init!"


def test_level1_screen_secret_persistence_and_game_init_restoration(labels: Dict[str, int], clean_mpu: MPU, project_root: Path):
    """Verify that secrets on Level 1 screens (screen >= 8, e.g. TOLEM_01 = screen 9)
    are correctly collected, persist across respawn, and restore properly on game_init
    without being blocked by dirty or out-of-bounds bitmasks."""
    mpu = clean_mpu

    # Find labyrinth index containing TOLEM_01 (screen 9)
    import yaml
    with open(project_root / "world" / "project.yaml", "r", encoding="utf-8") as f:
        proj = yaml.safe_load(f)
    tolem_level_idx = next(i for i, lab in enumerate(proj.get("labyrinths", [])) if "TOLEM_01" in lab.get("screens", []))

    # Initialize level screens for tolem_level_idx to bake TOLEM_01 into Buffer A
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = tolem_level_idx
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Screen 9 is TOLEM_01. Secret at x=6, y=5 (code $64, 1x1, secret=True)
    # Check initial tile and blocking mask
    blk_addr = labels["SCREEN_BUF_A_BLK"]
    vram_addr = labels["SCREEN_BUF_A_VRAM"]
    offset = 5 * 40 + 6
    orig_blk = mpu.memory[blk_addr + offset]
    orig_tile = mpu.memory[vram_addr + offset]
    assert (orig_blk & 0x04) == 0x04, "TOLEM_01 at (6, 5) should be secret"
    assert orig_tile == 0x64

    # When incoming_col_idx = 6, Left Screen at col0 = 8 - 6 = 2.
    # Object at x=6 aligns with VRAM col 2 + 6 = 8!
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = tolem_level_idx
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1  # Screen 9 is Left Screen
    mpu.memory[labels["INCOMING_COL_IDX"]] = 6   # col0 = 8 - 6 = 2 -> cur_vram_x = 2 + 6 = 8
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0
    # row 5: dragon_y = 34 + 5 * 16 = 114
    mpu.memory[labels["DRAGON_Y"]] = 114
    mpu.memory[labels["ANIM_PHASE"] + 1] = 0
    mpu.memory[labels["BLOCKING_COL8"] + 5] = 0x04

    # Run init_flame_collision
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Collect the secret
    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Verify source buffer cleared
    assert mpu.memory[blk_addr + offset] == 0x00, "Secret mask must be cleared in source buffer"
    assert mpu.memory[vram_addr + offset] == 0x00, "Secret tile must be cleared in source buffer"

    # Verify screen 9 bitmask in screen_obj_destroyed:
    # Screen 9 offset is 9 * 8 = 72!
    destroyed_base = labels["SCREEN_OBJ_DESTROYED"]
    assert any(mpu.memory[destroyed_base + 72 + b] != 0 for b in range(8)), "Screen 9 destroyed bitmask must have bit set"
    # And screen 0 (offset 0) must NOT be corrupted!
    assert all(mpu.memory[destroyed_base + b] == 0x00 for b in range(8)), "Screen 0 destroyed bitmask must NOT be affected"

    # Simulate dragon respawn:
    mpu.memory[labels["SHOW_LEVEL_NAME_SCREEN"]] = 0x60
    run_subroutine(mpu, labels["RESPAWN_DRAGON"])
    assert mpu.memory[blk_addr + offset] == 0x00, "Secret remains collected across respawn"
    assert any(mpu.memory[destroyed_base + 72 + b] != 0 for b in range(8)), "Screen 9 destroyed bitmask must remain set across respawn"

    # Simulate brand new game: game_init
    mpu.memory[labels["SHOW_LEVEL_NAME_SCREEN"]] = 0x60
    run_subroutine(mpu, labels["GAME_INIT"])
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = tolem_level_idx
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Must be RESTORED in source buffer!
    assert (mpu.memory[blk_addr + offset] & 0x04) == 0x04, "Secret mask must be restored on game_init"
    assert mpu.memory[vram_addr + offset] == 0x64, "Secret tile must be restored on game_init"
    # Bitmask must be CLEARED for next game!
    assert mpu.memory[destroyed_base + 72] == 0x00, "Screen 9 destroyed bitmask must be cleared on game_init"


def test_fire_breathing_invincibility_against_blocking_objects(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that when dragon is breathing fire (fire_state != 0), blocking collisions do NOT crash/kill dragon."""
    mpu = clean_mpu

    # Place dragon at scanline 82 (row 3)
    mpu.memory[labels["DRAGON_Y"]] = 82
    mpu.memory[labels["ANIM_PHASE"] + 1] = 0

    # Put solid blocking obstacle flag ($01) at row 3
    for r in range(11):
        mpu.memory[labels["BLOCKING_COL8"] + r] = 0x00
        mpu.memory[labels["BLOCKING_COL9"] + r] = 0x00
    mpu.memory[labels["BLOCKING_COL8"] + 3] = 0x01

    # CASE 1: fire_state == 0 (not breathing fire) -> normal blocking collision!
    mpu.memory[labels["FIRE_STATE"]] = 0
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0x01, "Normal flight without fire must detect blocking obstacle (Carry SET)"

    # CASE 2: fire_state == 1 (expanding flame) -> INVINCIBLE!
    mpu.memory[labels["FIRE_STATE"]] = 1
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0x00, "Breathing fire (state 1) must be invincible to blocking obstacle (Carry CLEAR)"

    # CASE 3: fire_state == 2 (peak hold flame) -> INVINCIBLE!
    mpu.memory[labels["FIRE_STATE"]] = 2
    run_subroutine(mpu, labels["CHECK_DRAGON_BLOCKING_COLLISION"])
    assert (mpu.p & 0x01) == 0x00, "Breathing fire (state 2) must be invincible to blocking obstacle (Carry CLEAR)"

    # CASE 4: Full check_dragon_collisions with hardware hit (dragon_p0pf = 1: PF0 wall collision)
    mpu.memory[labels["DRAGON_DYING"]] = 0
    mpu.memory[labels["GAME_OVER_REASON"]] = 0
    mpu.memory[labels["DRAGON_P0PF"]] = 0x01  # Wall hit latched
    mpu.memory[labels["FIRE_STATE"]] = 2      # Breathing fire
    run_subroutine(mpu, labels["CHECK_DRAGON_COLLISIONS"])
    assert mpu.memory[labels["DRAGON_DYING"]] == 0, "Dragon must NOT start dying from wall collision while breathing fire"


def test_fire_breathing_still_collects_secrets(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that while breathing fire (fire_state != 0), dragon still collects secret objects."""
    mpu = clean_mpu

    # Screen 0 FOREST_01 secret at (x=34, y=8)
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 1  # LEVEL_02 (FOREST_01..09)
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 1  # screen 0 is left screen
    mpu.memory[labels["INCOMING_COL_IDX"]] = 34
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 0
    mpu.memory[labels["DRAGON_Y"]] = 162
    mpu.memory[labels["ANIM_PHASE"] + 1] = 0

    # Put secret flag in blocking_col8
    for r in range(11):
        mpu.memory[labels["BLOCKING_COL8"] + r] = 0x00
        mpu.memory[labels["BLOCKING_COL9"] + r] = 0x00
    mpu.memory[labels["BLOCKING_COL8"] + 8] = 0x04

    # Dragon is breathing fire!
    mpu.memory[labels["FIRE_STATE"]] = 2
    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])

    # Run check_dragon_secret_collision
    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])
    assert (mpu.p & 0x01) == 0x01, "Secret collection must succeed while breathing fire (Carry SET)"

    # Verify secret was erased in staging buffer
    blk_addr = labels["SCREEN_BUF_A_BLK"]
    offset = 8 * 40 + 34
    assert mpu.memory[blk_addr + offset] == 0x00, "Secret must be collected and cleared even when breathing fire"


def test_tail_mode_collects_interactive_object_197(labels: Dict[str, int], clean_mpu: MPU):
    """Verify that interactive object 197 on screen FOREST_09 is properly collected during tail mode."""
    mpu = clean_mpu

    # Level 0 (Forest: LEVEL_01, 9 screens: FOREST_01..FOREST_09)
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    run_subroutine(mpu, labels["INIT_LEVEL_SCREENS"])

    # Simulate entering tail mode after screen 8 (FOREST_09) finishes streaming
    mpu.memory[labels["LEVEL_SCREEN_POS"]] = 9  # lab_total_screens
    mpu.memory[labels["INCOMING_COL_IDX"]] = 0
    # Object 197 is at x=36, y=6 on screen 8 (FOREST_09).
    # When level_tail_cols = 12: vram_col0 = 12 - 40 = -28 ($E4).
    # vram_x = -28 + 36 = 8 -> reaches dragon at cols 8..9!
    mpu.memory[labels["LEVEL_TAIL_COLS"]] = 12
    mpu.memory[labels["DRAGON_Y"]] = 130
    mpu.memory[labels["ANIM_PHASE"] + 1] = 0
    mpu.memory[labels["FIRE_STATE"]] = 0
    mpu.memory[labels["LIVES"]] = 3
    mpu.memory[labels["SCORE"] + 0] = 0
    mpu.memory[labels["SCORE"] + 1] = 0
    mpu.memory[labels["SCORE"] + 2] = 0
    mpu.memory[labels["SCORE"] + 3] = 0

    for r in range(11):
        mpu.memory[labels["BLOCKING_COL8"] + r] = 0x00
        mpu.memory[labels["BLOCKING_COL9"] + r] = 0x00
    # Interactive flag ($02) for peasant at row 6
    mpu.memory[labels["BLOCKING_COL8"] + 6] = 0x02

    run_subroutine(mpu, labels["INIT_FLAME_COLLISION"])
    run_subroutine(mpu, labels["CHECK_DRAGON_SECRET_COLLISION"])

    # Must detect collision!
    assert (mpu.p & 0x01) == 0x01, "Peasant 197 in tail mode must be collected (Carry SET)"
    assert mpu.memory[labels["LIVES"]] == 4, "Peasant collection must award +1 life"
    assert mpu.memory[labels["SCORE"] + 3] == 5, "Peasant collection must award +5 score"




