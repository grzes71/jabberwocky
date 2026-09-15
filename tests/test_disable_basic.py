"""Tests for disabling BASIC ROM and INITAD vector configuration."""

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


def test_disable_basic_sets_portb_bit1(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that disable_basic sets bit 1 of PORTB ($D301) to 1, disabling BASIC ROM."""
    mpu = clean_mpu
    portb = labels["PORTB"]
    disable_basic_addr = labels["DISABLE_BASIC"]

    # Simulate Atari XL/XE cold boot with BASIC enabled (PORTB bit 1 = 0, bit 0 = 1 for OS ROM)
    mpu.memory[portb] = 0xFD & ~0x02  # 0xFD = %11111101 (BASIC disabled is bit 1=1; here bit 1=0)

    assert (mpu.memory[portb] & 0x02) == 0, "Initial simulated state must have BASIC enabled (bit 1=0)"

    run_subroutine(mpu, disable_basic_addr)

    # Verify bit 1 is set (BASIC disabled) and bit 0 is preserved (OS ROM active)
    assert (mpu.memory[portb] & 0x02) == 0x02, "PORTB bit 1 must be set to 1 to disable BASIC ROM"
    assert (mpu.memory[portb] & 0x01) == 0x01, "PORTB bit 0 must be 1 to keep OS ROM active"


def test_xex_contains_initad_vector(project_root: Path, labels: Dict[str, int]):
    """Verify that jabberwocky.xex contains an INITAD ($02E2) segment pointing to disable_basic."""
    xex_file = project_root / "jabberwocky.xex"
    assert xex_file.exists()
    data = xex_file.read_bytes()

    # Search for segment loaded to $02E2-$02E3
    disable_basic_addr = labels["DISABLE_BASIC"]
    found_initad = False

    idx = 2 if data[:2] == b"\xFF\xFF" else 0
    while idx < len(data):
        if idx + 4 > len(data):
            break
        if data[idx : idx + 2] == b"\xFF\xFF":
            idx += 2
            continue
        start = data[idx] | (data[idx + 1] << 8)
        end = data[idx + 2] | (data[idx + 3] << 8)
        idx += 4
        length = end - start + 1
        block = data[idx : idx + length]
        idx += length

        if start == 0x02E2 and end == 0x02E3:
            init_target = block[0] | (block[1] << 8)
            assert init_target == disable_basic_addr, (
                f"INITAD vector ({init_target:#06x}) must point to disable_basic ({disable_basic_addr:#06x})"
            )
            found_initad = True

    assert found_initad, "jabberwocky.xex must contain an INITAD ($02E2) segment"
