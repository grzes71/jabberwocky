"""Unit tests for Centered Level Name Screen (ANTIC Mode 2) in Jabberwocky."""

from pathlib import Path
from typing import Dict
import pytest
from py65.devices.mpu6502 import MPU

from test_scrolling import load_xex, parse_labels, run_subroutine


@pytest.fixture(scope="module")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def labels(project_root: Path) -> Dict[str, int]:
    lab_path = project_root / "gen" / "jabberwocky.lab"
    assert lab_path.exists(), "gen/jabberwocky.lab must exist"
    return parse_labels(lab_path)


@pytest.fixture
def clean_mpu(project_root: Path, labels: Dict[str, int]) -> MPU:
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)
    # Mock OS SETVBV vector with RTS so OS calls don't crash under py65
    mpu.memory[labels["SETVBV"]] = 0x60
    return mpu


def test_level_name_symbols_exist(labels: Dict[str, int]):
    """Verify that all symbols for the level name screen exist."""
    expected = [
        "SHOW_LEVEL_NAME_SCREEN",
        "UPDATE_LEVEL_NAME_SCREEN",
        "START_ACTION_FLIGHT",
        "DLIST_LEVEL_NAME",
        "LABYRINTHS_NAME_LO",
        "LABYRINTHS_NAME_HI",
        "GAME_SUBSTATE",
        "SUBSTATE_LEVEL_NAME",
        "SUBSTATE_PLAYING",
        "LEVEL_NAME_LUM",
        "LEVEL_NAME_STATE",
    ]
    for sym in expected:
        assert sym in labels, f"Missing symbol: {sym}"


def test_show_level_name_screen_emulation(clean_mpu: MPU, labels: Dict[str, int]):
    """Test that show_level_name_screen initializes ANTIC Mode 2 and centers level name."""
    mpu = clean_mpu
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0

    run_subroutine(mpu, labels["SHOW_LEVEL_NAME_SCREEN"])

    # 1. Verify substate is SUBSTATE_LEVEL_NAME (0)
    assert mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_LEVEL_NAME"]

    # 2. Verify display list points to dlist_level_name
    dlist_expected = labels["DLIST_LEVEL_NAME"]
    dlist_actual = mpu.memory[labels["SDLSTL"]] | (mpu.memory[labels["SDLSTH"]] << 8)
    assert dlist_actual == dlist_expected

    # 3. Verify text in STUB_VRAM: "Tulgey Forest" (13 chars) centered at col (40-13)//2 = 13
    stub_base = labels["STUB_VRAM"]
    # Cols 0..12 must be space ($00)
    for c in range(13):
        assert mpu.memory[stub_base + c] == 0, f"Col {c} should be space"

    # "Tulgey Forest": "Tulgey" (cols 13..18) are non-zero, col 19 is space ($00), "Forest" (cols 20..25) are non-zero
    for c in range(13, 19):
        assert mpu.memory[stub_base + c] != 0, f"Col {c} ('Tulgey') should contain text"
    assert mpu.memory[stub_base + 19] == 0, "Col 19 must be space ($00)"
    for c in range(20, 26):
        assert mpu.memory[stub_base + c] != 0, f"Col {c} ('Forest') should contain text"

    # Cols 26..39 must be space ($00)
    for c in range(26, 40):
        assert mpu.memory[stub_base + c] == 0, f"Col {c} should be space"

    # 4. Text luminance initially black (0)
    assert mpu.memory[labels["LEVEL_NAME_LUM"]] == 0
    assert mpu.memory[labels["COLPF1"]] == 0


def test_update_level_name_screen_full_cycle(clean_mpu: MPU, labels: Dict[str, int]):
    """Test the complete fade in -> hold -> fade out -> flight transition."""
    mpu = clean_mpu
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    mpu.memory[labels["STRIG0"]] = 1  # Trigger released (no fire button)
    mpu.memory[labels["FIRE_PRESSED"]] = 0

    run_subroutine(mpu, labels["SHOW_LEVEL_NAME_SCREEN"])
    assert mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_LEVEL_NAME"]

    # Simulate 120 frames (approx 2.4s) to complete fade in, hold, fade out
    for _ in range(120):
        mpu.memory[labels["STRIG0"]] = 1
        mpu.memory[labels["FIRE_PRESSED"]] = 0
        run_subroutine(mpu, labels["UPDATE_LEVEL_NAME_SCREEN"])
        if mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_PLAYING"]:
            break

    # After sequence completes, game must transition to SUBSTATE_PLAYING (1)
    assert mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_PLAYING"]

    # DLIST should now be dlist_game
    dlist_expected = labels["DLIST_GAME"]
    dlist_actual = mpu.memory[labels["SDLSTL"]] | (mpu.memory[labels["SDLSTH"]] << 8)
    assert dlist_actual == dlist_expected

    # DMACTL should have playfield + PMG enabled ($3E)
    assert mpu.memory[labels["SDMCTL"]] == 0x3E

    # GTIA PMG latching and Player 0 positioning must be restored
    assert mpu.memory[labels["GRACTL"]] == 3
    assert mpu.memory[labels["HPOSP0"]] == labels["DRAGON_START_X"]
    assert mpu.memory[labels["GPRIOR"]] == 0x09
    assert mpu.memory[labels["SIZEP0"]] == 0
    assert mpu.memory[labels["PMBASE"]] == (labels["PM_ADDR"] >> 8)


def test_update_level_name_screen_fire_fast_forward(clean_mpu: MPU, labels: Dict[str, int]):
    """Test that pressing FIRE on joystick fast-forwards the screen and transitions quickly."""
    mpu = clean_mpu
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0
    mpu.memory[labels["STRIG0"]] = 1
    mpu.memory[labels["FIRE_PRESSED"]] = 0

    run_subroutine(mpu, labels["SHOW_LEVEL_NAME_SCREEN"])

    # Advance 5 frames (fade in starts)
    for _ in range(5):
        run_subroutine(mpu, labels["UPDATE_LEVEL_NAME_SCREEN"])

    assert mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_LEVEL_NAME"]

    # Press FIRE on joystick (STRIG0 = 0)
    mpu.memory[labels["STRIG0"]] = 0
    mpu.memory[labels["FIRE_PRESSED"]] = 1

    # Should finish in under 15 frames due to acceleration
    finished = False
    for frame in range(15):
        run_subroutine(mpu, labels["UPDATE_LEVEL_NAME_SCREEN"])
        if mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_PLAYING"]:
            finished = True
            break

    assert finished, "Level name screen should fast-forward and transition on FIRE"
    assert mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_PLAYING"]


def test_respawn_dragon_shows_level_name(clean_mpu: MPU, labels: Dict[str, int]):
    """Test that respawning after dragon death returns to the level name screen."""
    mpu = clean_mpu
    mpu.memory[labels["CURRENT_LEVEL_IDX"]] = 0

    # Put game in playing state first
    mpu.memory[labels["GAME_SUBSTATE"]] = labels["SUBSTATE_PLAYING"]

    run_subroutine(mpu, labels["RESPAWN_DRAGON"])

    # Must be reset back to SUBSTATE_LEVEL_NAME (0)
    assert mpu.memory[labels["GAME_SUBSTATE"]] == labels["SUBSTATE_LEVEL_NAME"]
    dlist_expected = labels["DLIST_LEVEL_NAME"]
    dlist_actual = mpu.memory[labels["SDLSTL"]] | (mpu.memory[labels["SDLSTH"]] << 8)
    assert dlist_actual == dlist_expected
