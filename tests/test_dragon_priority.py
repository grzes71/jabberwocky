"""Tests for dragon sprite priority over playfield colors (GTIA PRIOR register)."""

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
def clean_mpu(project_root: Path) -> MPU:
    xex_file = project_root / "jabberwocky.xex"
    assert xex_file.exists(), "jabberwocky.xex must exist (run make all)"
    mem = bytearray(65536)
    load_xex(xex_file, mem)
    mpu = MPU(memory=mem)
    return mpu


def test_game_init_sets_dragon_foreground_priority(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that game_init configures PRIOR = $11 (bit 0 = 1: P0..3 > PF0..3 > BAK; bit 4 = 1: 5th player)."""
    mpu = clean_mpu

    # Run game_init
    run_subroutine(mpu, labels["GAME_INIT"])

    # GPRIOR shadow and hardware PRIOR must both be $11
    # Bit 0 ($01): Players in front of all playfield colors
    # Bit 4 ($10): 5th player mode for missiles
    # Bit 3 ($08): MUST BE 0 (no playfield priority over dragon)
    gprior_val = mpu.memory[labels["GPRIOR"]]
    prior_val = mpu.memory[labels["PRIOR"]]

    assert gprior_val == 0x11, f"GPRIOR must be 0x11, got {gprior_val:#04x}"
    assert prior_val == 0x11, f"PRIOR must be 0x11, got {prior_val:#04x}"
    assert (prior_val & 0x01) == 0x01, "Bit 0 must be set (Players > Playfield)"
    assert (prior_val & 0x08) == 0x00, "Bit 3 must be clear (Playfield must NOT cover dragon)"
    assert (prior_val & 0x10) == 0x10, "Bit 4 must be set (5th player mode for missiles)"


def test_dli_game_action_ensures_dragon_foreground_priority(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that dli_game_action explicitly sets PRIOR = $11 for the action area."""
    mpu = clean_mpu

    # Dirty PRIOR with an inverted priority
    mpu.memory[labels["PRIOR"]] = 0x04  # PF > PM

    # Push fake return address and status for RTI
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100)
    mpu.stPush(0x20)  # P register (interrupts disabled)
    mpu.memory[0x0100] = 0x00  # BRK
    mpu.pc = labels["DLI_GAME_ACTION"]

    steps = 0
    while mpu.pc != 0x0100 and steps < 1000:
        mpu.step()
        steps += 1

    prior_val = mpu.memory[labels["PRIOR"]]
    assert prior_val == 0x11, f"dli_game_action must set PRIOR to 0x11, got {prior_val:#04x}"


def test_dli_game_bottom_sets_status_bar_priority(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that dli_game_bottom sets PRIOR = $09 for the status bar overlay."""
    mpu = clean_mpu

    # Ensure PRIOR was initially $11 (action area)
    mpu.memory[labels["PRIOR"]] = 0x11

    # Push fake return address and status for RTI
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100)
    mpu.stPush(0x20)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DLI_GAME_BOTTOM"]

    steps = 0
    while mpu.pc != 0x0100 and steps < 1000:
        mpu.step()
        steps += 1

    prior_val = mpu.memory[labels["PRIOR"]]
    assert prior_val == 0x09, f"dli_game_bottom must set PRIOR to 0x09, got {prior_val:#04x}"
