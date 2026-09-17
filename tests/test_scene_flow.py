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
