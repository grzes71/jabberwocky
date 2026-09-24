"""Tests for Title screen smooth slide-up effect on transition from STATE_INTRO."""

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


def test_initial_slide_flag_is_enabled(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify title_need_slide starts at 1 in binary data."""
    mpu = clean_mpu
    assert mpu.memory[labels["TITLE_NEED_SLIDE"]] == 1


def test_title_init_with_slide_flag_activates_slide(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify title_init consumes title_need_slide and prepares double-buffered slide DLIST."""
    mpu = clean_mpu
    mpu.memory[labels["TITLE_NEED_SLIDE"]] = 1

    run_subroutine(mpu, labels["TITLE_INIT"])

    # Flag should be consumed
    assert mpu.memory[labels["TITLE_NEED_SLIDE"]] == 0
    # Slide should be active with 0 visible lines
    assert mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] == 1
    assert mpu.memory[labels["TITLE_SLIDE_LINES"]] == 0

    # DLIST should point to TITLE_SLIDE_DLIST0 ($6000)
    dlist_lo = mpu.memory[labels["SDLSTL"]]
    dlist_hi = mpu.memory[labels["SDLSTH"]]
    dlist_addr = dlist_lo | (dlist_hi << 8)
    assert dlist_addr == labels["TITLE_SLIDE_DLIST0"]

    # In frame 0: 199 blank lines (24 * DL_BLANK8 = 192 lines, + 1 * DL_BLANK7 = 7 lines), followed by DL_JVB
    buf = dlist_addr
    # First 24 bytes are DL_BLANK8 ($70)
    for i in range(24):
        assert mpu.memory[buf + i] == labels["DL_BLANK8"]
    # 25th byte is DL_BLANK7 ($60)
    assert mpu.memory[buf + 24] == labels["DL_BLANK7"]
    # 26th byte is DL_JVB ($41)
    assert mpu.memory[buf + 25] == labels["DL_JVB"]


def test_title_init_without_slide_flag_direct_display(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify title_init directly sets full dlist_title when title_need_slide is 0."""
    mpu = clean_mpu
    mpu.memory[labels["TITLE_NEED_SLIDE"]] = 0

    run_subroutine(mpu, labels["TITLE_INIT"])

    assert mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] == 0
    dlist_lo = mpu.memory[labels["SDLSTL"]]
    dlist_hi = mpu.memory[labels["SDLSTH"]]
    dlist_addr = dlist_lo | (dlist_hi << 8)
    assert dlist_addr == labels["DLIST_TITLE"]
    # PMG players enabled ($3A) and GTIA player active (GRACTL=2)
    assert mpu.memory[labels["SDMCTL"]] == 0x3A
    assert mpu.memory[labels["GRACTL"]] == 2


def test_update_title_slide_advances_lines(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify update_title_slide steps visible lines and toggles buffer to DLIST1 ($6100)."""
    mpu = clean_mpu
    mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] = 1
    mpu.memory[labels["TITLE_SLIDE_LINES"]] = 0
    mpu.memory[labels["TITLE_SLIDE_BUF_IDX"]] = 0

    run_subroutine(mpu, labels["UPDATE_TITLE_SLIDE"])

    assert mpu.memory[labels["TITLE_SLIDE_LINES"]] == labels["TITLE_SLIDE_STEP"]  # 2
    assert mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] == 1

    # Buffer toggled to TITLE_SLIDE_DLIST1 ($6100)
    dlist_lo = mpu.memory[labels["SDLSTL"]]
    dlist_hi = mpu.memory[labels["SDLSTH"]]
    dlist_addr = dlist_lo | (dlist_hi << 8)
    assert dlist_addr == labels["TITLE_SLIDE_DLIST1"]


def test_update_title_slide_completes_at_total_lines(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that when lines reach 175, slide completes and switches to dlist_title."""
    mpu = clean_mpu
    mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] = 1
    mpu.memory[labels["TITLE_SLIDE_LINES"]] = 174  # next step will reach 176 >= 175
    mpu.memory[labels["TITLE_SLIDE_BUF_IDX"]] = 0

    run_subroutine(mpu, labels["UPDATE_TITLE_SLIDE"])

    assert mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] == 0
    dlist_lo = mpu.memory[labels["SDLSTL"]]
    dlist_hi = mpu.memory[labels["SDLSTH"]]
    dlist_addr = dlist_lo | (dlist_hi << 8)
    assert dlist_addr == labels["DLIST_TITLE"]
    assert mpu.memory[labels["SDMCTL"]] == 0x3A
    assert mpu.memory[labels["GRACTL"]] == 2


def test_fire_during_slide_skips_directly_to_game(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify pressing FIRE while slide is active skips directly to STATE_GAME."""
    mpu = clean_mpu
    mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] = 1
    mpu.memory[labels["FIRE_PRESSED"]] = 1
    mpu.memory[labels["GAME_STATE"]] = labels["STATE_TITLE"]

    run_subroutine(mpu, labels["TITLE_RUN"])

    assert mpu.memory[labels["FIRE_PRESSED"]] == 0
    assert mpu.memory[labels["GAME_STATE"]] == labels["STATE_GAME"]
    assert mpu.memory[labels["TITLE_SLIDE_ACTIVE"]] == 0
