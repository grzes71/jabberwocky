"""Unit and py65 tests for game state transitions and scene flow."""

from pathlib import Path
from typing import Dict
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


def test_initial_state_is_intro(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that initial game_state in binary data is STATE_INTRO."""
    mpu = clean_mpu
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_INTRO"], (
        f"Initial game_state must be STATE_INTRO ({labels['STATE_INTRO']}), "
        f"got {mpu.memory[labels['GAME_STATE']]}"
    )


def test_intro_run_transitions_to_title(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that after intro fade completes, intro_run transitions to STATE_TITLE."""
    mpu = clean_mpu
    # Set fade mode to FADE_MODE_DONE (3)
    mpu.memory[labels["INTRO_FADE_MODE"]] = labels["FADE_MODE_DONE"]
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_INTRO"]

    run_subroutine(mpu, labels["INTRO_RUN"])

    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TITLE"], (
        f"Expected transition to STATE_TITLE ({labels['STATE_TITLE']}), "
        f"got {mpu.memory[labels['GAME_STATE']]}"
    )


def test_intro_run_fire_triggers_immediate_fade_out(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that pressing FIRE while waiting triggers immediate fade-out."""
    mpu = clean_mpu
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_INTRO"]
    mpu.memory[labels["INTRO_FADE_MODE"]] = labels["FADE_MODE_WAIT"]
    mpu.memory[labels["INTRO_WAIT_TIMER"]] = labels["INTRO_WAIT_DELAY"]
    mpu.memory[labels["FIRE_PRESSED"]] = 1

    run_subroutine(mpu, labels["INTRO_RUN"])

    assert mpu.memory[labels["FIRE_PRESSED"]] == 0, "FIRE flag must be consumed"
    assert mpu.memory[labels["INTRO_FADE_MODE"]] == labels["FADE_MODE_OUT"], "Should transition to FADE_MODE_OUT"
    assert mpu.memory[labels["INTRO_FADE_LINE"]] == 3, "Fade out starts from bottom line (3)"
    assert mpu.memory[labels["INTRO_FADE_TIMER"]] == labels["FADE_OUT_DELAY"]


def test_intro_run_wait_timeout_triggers_fade_out(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that if FIRE is not pressed, intro screen waits 2 seconds (100 frames) then fades out."""
    mpu = clean_mpu
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_INTRO"]
    mpu.memory[labels["INTRO_FADE_MODE"]] = labels["FADE_MODE_WAIT"]
    mpu.memory[labels["INTRO_WAIT_TIMER"]] = labels["INTRO_WAIT_DELAY"]
    mpu.memory[labels["FIRE_PRESSED"]] = 0

    assert labels["INTRO_WAIT_DELAY"] == 100, "INTRO_WAIT_DELAY must be 100 frames (2 seconds at 50Hz)"

    # Run for 99 frames - should stay in FADE_MODE_WAIT
    for remaining in range(100, 1, -1):
        assert mpu.memory[labels["INTRO_WAIT_TIMER"]] == remaining
        run_subroutine(mpu, labels["INTRO_RUN"])
        assert mpu.memory[labels["INTRO_FADE_MODE"]] == labels["FADE_MODE_WAIT"]

    # Frame 100: timer reaches 0, triggers FADE_MODE_OUT
    assert mpu.memory[labels["INTRO_WAIT_TIMER"]] == 1
    run_subroutine(mpu, labels["INTRO_RUN"])

    assert mpu.memory[labels["INTRO_WAIT_TIMER"]] == 0
    assert mpu.memory[labels["INTRO_FADE_MODE"]] == labels["FADE_MODE_OUT"], (
        "After 2 seconds without FIRE, should automatically transition to FADE_MODE_OUT"
    )
    assert mpu.memory[labels["INTRO_FADE_LINE"]] == 3
    assert mpu.memory[labels["INTRO_FADE_TIMER"]] == labels["FADE_OUT_DELAY"]


def test_intro_fade_in_completion_initializes_wait_timer(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that completing fade-in of line 3 sets FADE_MODE_WAIT and INTRO_WAIT_DELAY."""
    mpu = clean_mpu
    mpu.memory[labels["INTRO_FADE_MODE"]] = labels["FADE_MODE_IN"]
    mpu.memory[labels["INTRO_FADE_LINE"]] = 3
    mpu.memory[labels["INTRO_FADE_TIMER"]] = 1
    # Line 3 color is at $0C, next increment will reach $0E (max)
    mpu.memory[labels["INTRO_LINE_COL3"]] = 0x0C

    run_subroutine(mpu, labels["UPDATE_INTRO_FADE"])

    assert mpu.memory[labels["INTRO_LINE_COL3"]] == 0x0E
    assert mpu.memory[labels["INTRO_FADE_MODE"]] == labels["FADE_MODE_WAIT"]
    assert mpu.memory[labels["INTRO_WAIT_TIMER"]] == labels["INTRO_WAIT_DELAY"]


def test_title_run_transitions_to_game(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that pressing FIRE on the title screen transitions to STATE_GAME."""
    mpu = clean_mpu
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_TITLE"]

    run_subroutine(mpu, labels["TITLE_RUN"])

    assert mpu.memory[labels["FIRE_PRESSED"]] == 0, "FIRE flag must be consumed by title_run"
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_GAME"], (
        f"Expected transition to STATE_GAME ({labels['STATE_GAME']}), "
        f"got {mpu.memory[labels['GAME_STATE']]}"
    )


def test_gameover_run_transitions_to_top_scores(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that pressing FIRE on the game over screen transitions to STATE_TOP_SCORES."""
    mpu = clean_mpu
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_GAME_OVER"]

    run_subroutine(mpu, labels["GAMEOVER_RUN"])

    assert mpu.memory[labels["FIRE_PRESSED"]] == 0, "FIRE flag must be consumed by gameover_run"
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"], (
        f"Expected transition to STATE_TOP_SCORES ({labels['STATE_TOP_SCORES']}), "
        f"got {mpu.memory[labels['GAME_STATE']]}"
    )


def test_full_loop_intro_never_revisited(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify full loop: Intro -> Title -> Game -> Game Over -> Top Scores -> Title -> Game."""
    mpu = clean_mpu

    # 1. Start at Intro
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_INTRO"]
    mpu.memory[labels["INTRO_FADE_MODE"]] = labels["FADE_MODE_DONE"]
    run_subroutine(mpu, labels["INTRO_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TITLE"]

    # 2. Title -> Game
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    run_subroutine(mpu, labels["TITLE_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_GAME"]

    # 3. Game ends -> Game Over
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_GAME_OVER"]

    # 4. Game Over -> Top Scores
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    run_subroutine(mpu, labels["GAMEOVER_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TOP_SCORES"]

    # 5. Top Scores -> Title (NOT Intro)
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    run_subroutine(mpu, labels["TOP_SCORES_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_TITLE"]

    # 6. Title -> Game (direct start, Intro is bypassed)
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    run_subroutine(mpu, labels["TITLE_RUN"])
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_GAME"]


def test_gameover_init_border_matches_background_defeat(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify gameover_init sets border (COLOR4) equal to background (COLOR2) on defeat ($32)."""
    mpu = clean_mpu
    mpu.memory[labels["GAME_OVER_REASON"]] = 1  # Not REASON_SUCCESS (0)

    run_subroutine(mpu, labels["GAMEOVER_INIT"])

    assert mpu.memory[labels["COLOR2"]] == 0x32
    assert mpu.memory[labels["COLOR4"]] == 0x32
    assert mpu.memory[labels["COLOR4"]] == mpu.memory[labels["COLOR2"]]


def test_gameover_init_border_matches_background_victory(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify gameover_init sets border (COLOR4) equal to background (COLOR2) on victory ($C4)."""
    mpu = clean_mpu
    mpu.memory[labels["GAME_OVER_REASON"]] = labels["REASON_SUCCESS"]

    run_subroutine(mpu, labels["GAMEOVER_INIT"])

    assert mpu.memory[labels["COLOR2"]] == 0xC4
    assert mpu.memory[labels["COLOR4"]] == 0xC4
    assert mpu.memory[labels["COLOR4"]] == mpu.memory[labels["COLOR2"]]
