"""Unit and py65 integration tests for Top 10 High Scores and Joystick Name Entry."""

from pathlib import Path
from typing import Dict, List
import pytest
from py65.devices.mpu6502 import MPU
from tests.test_flame_collision import parse_labels, load_xex, run_subroutine


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def labels(project_root: Path) -> Dict[str, int]:
    lab_file = project_root / "gen" / "jabberwocky.lab"
    assert lab_file.exists(), "gen/jabberwocky.lab must exist (run make all)"
    return parse_labels(lab_file)


@pytest.fixture
def clean_mpu(project_root: Path, labels: Dict[str, int]) -> MPU:
    xex_file = project_root / "jabberwocky.xex"
    assert xex_file.exists(), "jabberwocky.xex must exist (run make all)"
    mem = bytearray(65536)
    load_xex(xex_file, mem)
    mpu = MPU(memory=mem)
    # Mock OS SETVBV vector with RTS so OS calls don't crash under py65
    mpu.memory[labels["SETVBV"]] = 0x60
    return mpu


def get_table_scores(mpu: MPU, labels: Dict[str, int]) -> List[int]:
    """Read all 10 scores from hs_scores as integers."""
    base = labels["HS_SCORES"]
    scores = []
    for i in range(10):
        d0 = mpu.memory[base + i * 4]
        d1 = mpu.memory[base + i * 4 + 1]
        d2 = mpu.memory[base + i * 4 + 2]
        d3 = mpu.memory[base + i * 4 + 3]
        scores.append(d0 * 1000 + d1 * 100 + d2 * 10 + d3)
    return scores


def set_player_score(mpu: MPU, labels: Dict[str, int], score_val: int) -> None:
    """Write an integer score (0..9999) into the 4 decimal SCORE digits."""
    addr = labels["SCORE"]
    mpu.memory[addr] = (score_val // 1000) % 10
    mpu.memory[addr + 1] = (score_val // 100) % 10
    mpu.memory[addr + 2] = (score_val // 10) % 10
    mpu.memory[addr + 3] = score_val % 10


def test_top_scores_symbols_exist(labels: Dict[str, int]):
    """Verify that all state machine and high score symbols exist."""
    required = [
        "STATE_TOP_SCORES",
        "STATE_ENTER_NAME",
        "TOP_SCORES_INIT",
        "TOP_SCORES_RUN",
        "ENTER_NAME_INIT",
        "ENTER_NAME_RUN",
        "CHECK_SCORE_QUALIFIED",
        "COMPARE_SCORE_ENTRY",
        "INSERT_HIGH_SCORE",
        "HS_SCORES",
        "HS_NAMES",
        "SCORE_PROCESSED",
        "CURSOR_POS",
        "NAME_INDICES",
        "DLIST_TOP_SCORES",
    ]
    for sym in required:
        assert sym in labels, f"Required symbol '{sym}' not found in labels"


def test_default_high_scores_sorted(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify the initial 10 high scores are strictly sorted in descending order."""
    scores = get_table_scores(clean_mpu, labels)
    assert len(scores) == 10
    for i in range(len(scores) - 1):
        assert scores[i] > scores[i + 1], (
            f"Table must be strictly descending: scores[{i}]={scores[i]} <= scores[{i+1}]={scores[i+1]}"
        )
    # Check bounds
    assert scores[0] == 500
    assert scores[9] == 20


def test_check_score_qualified(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify check_score_qualified sets Carry only if SCORE > 10th entry."""
    mpu = clean_mpu

    # Case 1: score = 0 -> Not qualified (Carry = 0)
    set_player_score(mpu, labels, 0)
    run_subroutine(mpu, labels["CHECK_SCORE_QUALIFIED"])
    assert (mpu.p & 0x01) == 0, "Score 0 must not qualify"

    # Case 2: score = 20 (equal to 10th score 20) -> Not qualified (strict >)
    set_player_score(mpu, labels, 20)
    run_subroutine(mpu, labels["CHECK_SCORE_QUALIFIED"])
    assert (mpu.p & 0x01) == 0, "Score equal to 10th must not qualify (strict >)"

    # Case 3: score = 21 -> Qualifies (Carry = 1)
    set_player_score(mpu, labels, 21)
    run_subroutine(mpu, labels["CHECK_SCORE_QUALIFIED"])
    assert (mpu.p & 0x01) == 1, "Score 21 must qualify against 10th entry (20)"

    # Case 4: score = 320 -> Qualifies (Carry = 1)
    set_player_score(mpu, labels, 320)
    run_subroutine(mpu, labels["CHECK_SCORE_QUALIFIED"])
    assert (mpu.p & 0x01) == 1, "Score 320 must qualify"


def test_insert_high_score_rank_1(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify inserting a new #1 score shifts all existing scores down and drops the 10th."""
    mpu = clean_mpu
    initial_scores = get_table_scores(mpu, labels)

    set_player_score(mpu, labels, 999)
    # Set entered name indices to [7, 4, 17, 14, 36] = "HERO "
    name_addr = labels["NAME_INDICES"]
    mpu.memory[name_addr : name_addr + 5] = bytearray([7, 4, 17, 14, 36])

    run_subroutine(mpu, labels["INSERT_HIGH_SCORE"])

    new_scores = get_table_scores(mpu, labels)
    assert new_scores[0] == 999
    # Previous #1 (500) shifted to #2
    assert new_scores[1] == initial_scores[0]
    # Previous #9 (50) shifted to #10
    assert new_scores[9] == initial_scores[8]
    # Old 10th score (20) discarded
    assert 20 not in new_scores


def test_insert_high_score_middle(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify inserting a middle-tier score (e.g. 260) inserts at rank 5 (between 300 and 250)."""
    mpu = clean_mpu
    # Table has: 500, 400, 350, 300, 250, 200, 150, 100, 50, 20
    set_player_score(mpu, labels, 260)
    run_subroutine(mpu, labels["INSERT_HIGH_SCORE"])

    new_scores = get_table_scores(mpu, labels)
    assert new_scores[4] == 260
    assert new_scores[3] == 300
    assert new_scores[5] == 250


def test_insert_high_score_last_slot(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify inserting score 25 replaces rank 10 directly without crashing or corrupting."""
    mpu = clean_mpu
    set_player_score(mpu, labels, 25)
    run_subroutine(mpu, labels["INSERT_HIGH_SCORE"])

    new_scores = get_table_scores(mpu, labels)
    assert new_scores[8] == 50
    assert new_scores[9] == 25


def test_joystick_name_entry_controls(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify joystick UP/DOWN changes character and LEFT/RIGHT moves cursor."""
    mpu = clean_mpu
    # Initialize name entry state
    run_subroutine(mpu, labels["ENTER_NAME_INIT"])

    assert mpu.memory[labels["CURSOR_POS"]] == 0
    assert mpu.memory[labels["NAME_INDICES"]] == 0  # 'A'

    stick = labels["STICK0"]

    # 1. Push UP (bit 0 = 0 -> $0E)
    mpu.memory[stick] = 0x0E
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])
    assert mpu.memory[labels["NAME_INDICES"]] == 1  # 'B'

    # Return stick to center ($0F)
    mpu.memory[stick] = 0x0F
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])

    # 2. Push RIGHT (bit 3 = 0 -> $07)
    mpu.memory[stick] = 0x07
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])
    assert mpu.memory[labels["CURSOR_POS"]] == 1  # Moved to slot 1

    # Return stick to center
    mpu.memory[stick] = 0x0F
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])

    # 3. Push DOWN (bit 1 = 0 -> $0D) on slot 1 (starts at 0 -> wraps to 36 = ' ')
    mpu.memory[stick] = 0x0D
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])
    assert mpu.memory[labels["NAME_INDICES"] + 1] == 36  # Wrapped to last char (space)

    # Return stick to center
    mpu.memory[stick] = 0x0F
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])

    # 4. Push LEFT (bit 2 = 0 -> $0B)
    mpu.memory[stick] = 0x0B
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])
    assert mpu.memory[labels["CURSOR_POS"]] == 0  # Back to slot 0


def test_gameover_transitions_to_top_scores(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify pressing FIRE on the existing GAME OVER screen transitions to STATE_TOP_SCORES."""
    mpu = clean_mpu
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_GAME_OVER"]
    mpu.memory[labels["FIRE_PRESSED"]] = 1

    run_subroutine(mpu, labels["GAMEOVER_RUN"])

    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"], (
        f"GAME OVER must transition to STATE_TOP_SCORES ({labels['STATE_TOP_SCORES']}), "
        f"got {mpu.memory[labels['GAME_STATE']]}"
    )
    assert mpu.memory[labels["FIRE_PRESSED"]] == 0


def test_top_scores_init_branches_to_enter_name_when_qualified(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify top_scores_init immediately routes qualifying scores to STATE_ENTER_NAME."""
    mpu = clean_mpu
    set_player_score(mpu, labels, 550)  # > 500 (new #1)
    mpu.memory[labels["SCORE_PROCESSED"]] = 0
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_TOP_SCORES"]

    run_subroutine(mpu, labels["TOP_SCORES_INIT"])

    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_ENTER_NAME"]
    assert mpu.memory[labels["SCORE_PROCESSED"]] == 1


def test_top_scores_init_stays_on_top_scores_when_not_qualified(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify top_scores_init stays on STATE_TOP_SCORES for non-qualifying scores."""
    mpu = clean_mpu
    set_player_score(mpu, labels, 10)  # < 20 (does not qualify)
    mpu.memory[labels["SCORE_PROCESSED"]] = 0
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_TOP_SCORES"]

    run_subroutine(mpu, labels["TOP_SCORES_INIT"])

    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"]
    assert mpu.memory[labels["SCORE_PROCESSED"]] == 1


def test_full_flow_gameover_to_name_entry_to_top_scores_to_title(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify full end-to-end sequence:

    GAME OVER -> FIRE -> TOP SCORES -> (qualifies) -> ENTER NAME -> FIRE -> TOP SCORES -> FIRE -> TITLE
    """
    mpu = clean_mpu

    # 1. In GAME OVER with score 450 (qualifies for #2)
    set_player_score(mpu, labels, 450)
    mpu.memory[labels["SCORE_PROCESSED"]] = 0
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_GAME_OVER"]
    mpu.memory[labels["FIRE_PRESSED"]] = 1

    # 2. Leave GAME OVER
    run_subroutine(mpu, labels["GAMEOVER_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"]

    # 3. TOP SCORES detects qualifying score and transitions to ENTER NAME
    run_subroutine(mpu, labels["TOP_SCORES_INIT"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_ENTER_NAME"]

    # 4. ENTER NAME initializes
    run_subroutine(mpu, labels["ENTER_NAME_INIT"])

    # 5. Confirm name with FIRE
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    run_subroutine(mpu, labels["ENTER_NAME_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"]

    # Table now has 450 at rank 2
    assert get_table_scores(mpu, labels)[1] == 450

    # 6. Re-enter TOP SCORES (score_processed is 1, so it displays table, no re-entry to ENTER NAME)
    run_subroutine(mpu, labels["TOP_SCORES_INIT"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"]

    # 7. Press FIRE on TOP SCORES to return to TITLE screen
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    run_subroutine(mpu, labels["TOP_SCORES_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TITLE"]
    assert mpu.memory[labels["SCORE_PROCESSED"]] == 0  # Reset for next game


def test_top_scores_display_list_structure(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify dlist_top_scores contains DL_BLANK4 between each of the 10 score lines."""
    mpu = clean_mpu
    addr = labels["DLIST_TOP_SCORES"]

    # 2 blank8 lines: $70, $70
    assert mpu.memory[addr] == 0x70
    assert mpu.memory[addr + 1] == 0x70
    addr += 2

    # Row 0: DL_MODE_2 | DL_LMS ($42), a(STUB_VRAM)
    assert mpu.memory[addr] == 0x42
    stub_vram_addr = mpu.memory[addr + 1] | (mpu.memory[addr + 2] << 8)
    assert stub_vram_addr == labels["STUB_VRAM"]
    addr += 3

    # DL_BLANK2 ($10)
    assert mpu.memory[addr] == 0x10
    addr += 1

    # Row 1: DL_MODE_2 ($02)
    assert mpu.memory[addr] == 0x02
    addr += 1

    # DL_BLANK4 ($30)
    assert mpu.memory[addr] == 0x30
    addr += 1

    # Row 2: DL_MODE_2 ($02)
    assert mpu.memory[addr] == 0x02
    addr += 1

    # DL_BLANK4 ($30)
    assert mpu.memory[addr] == 0x30
    addr += 1

    # 10 score rows with DL_BLANK4 ($30) between each pair
    for i in range(10):
        # Score line: DL_MODE_2 ($02)
        assert mpu.memory[addr] == 0x02, f"Expected DL_MODE_2 at score line {i}"
        addr += 1
        if i < 9:
            # Spacing between scores: DL_BLANK4 ($30)
            assert mpu.memory[addr] == 0x30, f"Expected DL_BLANK4 after score line {i}"
            addr += 1

    # DL_BLANK8 ($70) before prompt
    assert mpu.memory[addr] == 0x70
    addr += 1

    # Row 13: Prompt DL_MODE_2 ($02)
    assert mpu.memory[addr] == 0x02
    addr += 1

    # End with DL_JVB ($41), a(dlist_top_scores)
    assert mpu.memory[addr] == 0x41
    jump_dest = mpu.memory[addr + 1] | (mpu.memory[addr + 2] << 8)
    assert jump_dest == labels["DLIST_TOP_SCORES"]


def test_top_scores_init_activates_dlist_and_renders_rows(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify top_scores_init sets DLIST to dlist_top_scores and renders rows 0..13."""
    mpu = clean_mpu
    # Score already processed so top_scores_init directly renders table
    mpu.memory[labels["SCORE_PROCESSED"]] = 1

    run_subroutine(mpu, labels["TOP_SCORES_INIT"])

    # Verify background and border colors are both blue ($70)
    assert mpu.memory[labels["COLOR2"]] == 0x70
    assert mpu.memory[labels["COLPF2"]] == 0x70
    assert mpu.memory[labels["COLOR4"]] == 0x70
    assert mpu.memory[labels["COLBK"]] == 0x70

    # Verify SDLSTL/SDLSTH and DLISTL/DLISTH set to DLIST_TOP_SCORES
    dlist_expected = labels["DLIST_TOP_SCORES"]
    dlist_lo = dlist_expected & 0xFF
    dlist_hi = (dlist_expected >> 8) & 0xFF

    assert mpu.memory[labels["SDLSTL"]] == dlist_lo
    assert mpu.memory[labels["SDLSTH"]] == dlist_hi
    assert mpu.memory[labels["DLISTL"]] == dlist_lo
    assert mpu.memory[labels["DLISTH"]] == dlist_hi

    # Verify text in STUB_VRAM:
    stub_base = labels["STUB_VRAM"]

    # Row 0: "JABBERWOCKY" at col 14
    title_bytes = [mpu.memory[stub_base + 0 * 40 + 14 + k] for k in range(11)]
    expected_title = [mpu.memory[labels["TS_TXT_TITLE"] + 1 + k] for k in range(11)]
    assert title_bytes == expected_title

    # Row 3: Score rank 1 (" 1.  DRACO  0500")
    draco_bytes = [mpu.memory[stub_base + 3 * 40 + 17 + k] for k in range(5)]
    expected_draco = [mpu.memory[labels["HS_NAMES"] + k] for k in range(5)]
    assert draco_bytes == expected_draco

    # Row 12: Score rank 10 ("10.  TOVES  0020")
    toves_bytes = [mpu.memory[stub_base + 12 * 40 + 17 + k] for k in range(5)]
    expected_toves = [mpu.memory[labels["HS_NAMES"] + 9 * 5 + k] for k in range(5)]
    assert toves_bytes == expected_toves


