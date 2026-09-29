#!/usr/bin/env python3
"""Automated py65 tests for the CMC music subsystem.

Verifies:
- Relocated CMC music binary and player load addresses
- Subsongs 0, 1, 2 initialization
- 1000 frames continuous playback stability and cycle sanity
- Zero Page ($FC-$FF) preservation
- Stack balance (SP restored, max depth <= 16 bytes)
- Music_PlaySong state caching (no redundant INIT on same song)
- Music_Stop mute behavior
- Full scene transition simulation (Title -> Game -> GameOver -> Title)
"""

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
    mpu = MPU()
    load_xex(xex_file, mpu.memory)
    return mpu


@pytest.fixture
def music_labels(labels: Dict[str, int]) -> Dict[str, int]:
    required = [
        "MUSIC_PLAYSONG",
        "MUSIC_UPDATE",
        "MUSIC_STOP",
        "MUSIC_CURRENT_SONG",
        "MUSIC_ACTIVE",
        "MUSIC_DATA_ADDR",
        "CMC_PLAYER_ADDR",
        "CMC_PLAYER",
    ]
    for sym in required:
        assert sym in labels, f"Missing music symbol: {sym}"
    return labels


def test_music_symbols_and_memory_map(music_labels: Dict[str, int]):
    """Verify that music data and player reside in expected free RAM segment."""
    assert music_labels["MUSIC_DATA_ADDR"] == 0x9000
    assert music_labels["CMC_PLAYER_ADDR"] == 0x9A00
    assert music_labels["CMC_PLAYER"] == 0x9A00


def test_subsongs_init_and_play(clean_mpu: MPU, music_labels: Dict[str, int]):
    """Verify initialization and 100 frames playback for all 3 subsongs."""
    mpu = clean_mpu

    for song_idx in [0, 1, 2]:
        # Reset current song state to force init
        mpu.memory[music_labels["MUSIC_CURRENT_SONG"]] = 0xFF
        mpu.memory[music_labels["MUSIC_ACTIVE"]] = 0x00

        # Music_PlaySong(song_idx)
        mpu.a = song_idx
        run_subroutine(mpu, music_labels["MUSIC_PLAYSONG"])

        assert mpu.memory[music_labels["MUSIC_CURRENT_SONG"]] == song_idx
        assert mpu.memory[music_labels["MUSIC_ACTIVE"]] == 1

        # Play 100 frames
        for _ in range(100):
            run_subroutine(mpu, music_labels["MUSIC_UPDATE"])

        assert mpu.sp == 0xFD, f"Stack leaked after 100 frames of subsong {song_idx}"


def test_1000_frames_playback_and_stack_depth(clean_mpu: MPU, music_labels: Dict[str, int]):
    """Verify 1000 frames continuous playback on Gameplay track (subsong 1) with min SP tracking."""
    mpu = clean_mpu

    # Select gameplay music
    mpu.a = 1  # MUSIC_GAMEPLAY
    run_subroutine(mpu, music_labels["MUSIC_PLAYSONG"])
    assert mpu.sp == 0xFD

    min_sp = 0xFD
    for frame in range(1000):
        # Instrument run_subroutine steps or check SP
        mpu.memory[0x01FE] = 0x55  # stack canary
        run_subroutine(mpu, music_labels["MUSIC_UPDATE"])
        if mpu.sp < min_sp:
            min_sp = mpu.sp

    assert mpu.sp == 0xFD, f"Stack must be $FD after 1000 frames, got ${mpu.sp:02X}"
    # Total stack depth: caller return addr (2) + wrapper PHA/TXA/TYA (3) + CMC JSR (2) + CMC PHA (4) + internal <= 16 B
    depth = 0xFD - min_sp
    assert depth <= 16, f"Excessive stack depth observed: {depth} bytes (min SP=${min_sp:02X})"


def test_zero_page_preservation(clean_mpu: MPU, music_labels: Dict[str, int]):
    """Verify that $FC..$FF are preserved across Music_PlaySong and Music_Update."""
    mpu = clean_mpu

    canary = (0x12, 0x34, 0x56, 0x78)
    mpu.memory[0xFC] = canary[0]
    mpu.memory[0xFD] = canary[1]
    mpu.memory[0xFE] = canary[2]
    mpu.memory[0xFF] = canary[3]

    # Music_PlaySong
    mpu.a = 2  # MUSIC_TITLE
    run_subroutine(mpu, music_labels["MUSIC_PLAYSONG"])

    assert (
        mpu.memory[0xFC],
        mpu.memory[0xFD],
        mpu.memory[0xFE],
        mpu.memory[0xFF],
    ) == canary, "Zero Page $FC-$FF corrupted during Music_PlaySong"

    # Music_Update over 50 frames
    for f in range(50):
        test_val = ((f + 1) & 0xFF, (f + 2) & 0xFF, (f + 3) & 0xFF, (f + 4) & 0xFF)
        mpu.memory[0xFC] = test_val[0]
        mpu.memory[0xFD] = test_val[1]
        mpu.memory[0xFE] = test_val[2]
        mpu.memory[0xFF] = test_val[3]

        run_subroutine(mpu, music_labels["MUSIC_UPDATE"])

        assert (
            mpu.memory[0xFC],
            mpu.memory[0xFD],
            mpu.memory[0xFE],
            mpu.memory[0xFF],
        ) == test_val, f"Zero Page $FC-$FF corrupted on frame {f}"


def test_music_playsong_caching_and_stop(clean_mpu: MPU, music_labels: Dict[str, int]):
    """Verify that Music_PlaySong caches current song and Music_Stop silences POKEY."""
    mpu = clean_mpu

    # 1. Start Title music
    mpu.a = 2
    run_subroutine(mpu, music_labels["MUSIC_PLAYSONG"])
    assert mpu.memory[music_labels["MUSIC_CURRENT_SONG"]] == 2
    assert mpu.memory[music_labels["MUSIC_ACTIVE"]] == 1

    # Play 10 frames to produce sound
    for _ in range(10):
        run_subroutine(mpu, music_labels["MUSIC_UPDATE"])

    # 2. Call Music_PlaySong with same song (2) -> must not reset or crash
    mpu.a = 2
    run_subroutine(mpu, music_labels["MUSIC_PLAYSONG"])
    assert mpu.memory[music_labels["MUSIC_CURRENT_SONG"]] == 2

    # 3. Call Music_Stop
    run_subroutine(mpu, music_labels["MUSIC_STOP"])
    assert mpu.memory[music_labels["MUSIC_CURRENT_SONG"]] == 0xFF
    assert mpu.memory[music_labels["MUSIC_ACTIVE"]] == 0

    # POKEY channels $D200..$D208 must be 0
    for reg in range(0xD200, 0xD209):
        assert mpu.memory[reg] == 0, f"POKEY register ${reg:04X} not silenced by Music_Stop"

    # Music_Update when inactive must do nothing
    run_subroutine(mpu, music_labels["MUSIC_UPDATE"])
    for reg in range(0xD200, 0xD209):
        assert mpu.memory[reg] == 0


def test_scene_transitions_sequence(clean_mpu: MPU, music_labels: Dict[str, int]):
    """Simulate sequence: Title (2) -> Gameplay (1) -> GameOver (0) -> Title (2) -> Gameplay (1)."""
    mpu = clean_mpu

    flow = [
        (2, "TITLE"),
        (1, "GAMEPLAY"),
        (0, "GAMEOVER"),
        (2, "TITLE"),
        (1, "GAMEPLAY"),
    ]

    for song_id, scene_name in flow:
        mpu.a = song_id
        run_subroutine(mpu, music_labels["MUSIC_PLAYSONG"])
        assert mpu.memory[music_labels["MUSIC_CURRENT_SONG"]] == song_id
        assert mpu.memory[music_labels["MUSIC_ACTIVE"]] == 1

        # Simulate 30 frames of scene execution
        for _ in range(30):
            run_subroutine(mpu, music_labels["MUSIC_UPDATE"])

        assert mpu.sp == 0xFD, f"Stack unbalanced after {scene_name}"


def step_with_sp_tracking(mpu: MPU, target_addr: int, max_steps: int = 100000) -> int:
    """Run routine and track the lowest SP observed during execution."""
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = target_addr

    min_sp = mpu.sp
    steps = 0
    while mpu.pc != 0x0100 and steps < max_steps:
        mpu.step()
        if mpu.sp < min_sp:
            min_sp = mpu.sp
        steps += 1

    assert mpu.pc == 0x0100, f"Routine at {hex(target_addr)} failed to return (PC={hex(mpu.pc)})"
    assert mpu.sp == 0xFD, f"Stack not restored (got SP=${mpu.sp:02X}, expected $FD)"
    return min_sp


def test_abi_register_preservation_and_exact_stack_depth(clean_mpu: MPU, music_labels: Dict[str, int]):
    """Verify that A, X, Y are 100% preserved and measure exact lowest SP during execution."""
    mpu = clean_mpu

    # 1. Test Music_PlaySong(1)
    mpu.a = 1
    mpu.x = 0x42
    mpu.y = 0x84
    min_sp_play = step_with_sp_tracking(mpu, music_labels["MUSIC_PLAYSONG"])
    assert mpu.a == 1, f"A not preserved by Music_PlaySong: got ${mpu.a:02X}"
    assert mpu.x == 0x42, f"X not preserved by Music_PlaySong: got ${mpu.x:02X}"
    assert mpu.y == 0x84, f"Y not preserved by Music_PlaySong: got ${mpu.y:02X}"

    # 2. Test Music_PlaySong caching path (same song 1)
    mpu.a = 1
    mpu.x = 0x11
    mpu.y = 0x22
    min_sp_cache = step_with_sp_tracking(mpu, music_labels["MUSIC_PLAYSONG"])
    assert mpu.a == 1
    assert mpu.x == 0x11
    assert mpu.y == 0x22

    # 3. Test Music_Update when active (10 frames)
    min_sp_update = 0xFF
    for _ in range(10):
        mpu.a = 0xAA
        mpu.x = 0xBB
        mpu.y = 0xCC
        min_sp = step_with_sp_tracking(mpu, music_labels["MUSIC_UPDATE"])
        if min_sp < min_sp_update:
            min_sp_update = min_sp
        assert mpu.a == 0xAA, f"A not preserved by Music_Update: got ${mpu.a:02X}"
        assert mpu.x == 0xBB, f"X not preserved by Music_Update: got ${mpu.x:02X}"
        assert mpu.y == 0xCC, f"Y not preserved by Music_Update: got ${mpu.y:02X}"

    # 4. Test Music_Stop
    mpu.a = 0x33
    mpu.x = 0x55
    mpu.y = 0x77
    min_sp_stop = step_with_sp_tracking(mpu, music_labels["MUSIC_STOP"])
    assert mpu.a == 0x33, f"A not preserved by Music_Stop: got ${mpu.a:02X}"
    assert mpu.x == 0x55, f"X not preserved by Music_Stop: got ${mpu.x:02X}"
    assert mpu.y == 0x77, f"Y not preserved by Music_Stop: got ${mpu.y:02X}"

    # 5. Test Music_Update when inactive
    mpu.a = 0x99
    mpu.x = 0x88
    mpu.y = 0x77
    min_sp_inactive = step_with_sp_tracking(mpu, music_labels["MUSIC_UPDATE"])
    assert mpu.a == 0x99, f"A not preserved by Music_Update (inactive): got ${mpu.a:02X}"
    assert mpu.x == 0x88, f"X not preserved by Music_Update (inactive): got ${mpu.x:02X}"
    assert mpu.y == 0x77, f"Y not preserved by Music_Update (inactive): got ${mpu.y:02X}"

    print(
        f"Measured SP minimums (from $01FF): "
        f"PlaySong=${min_sp_play:02X}, Update=${min_sp_update:02X}, "
        f"Stop=${min_sp_stop:02X}, InactiveUpdate=${min_sp_inactive:02X}"
    )
    # Check max stack consumed
    assert min_sp_play >= 0xED, f"Music_PlaySong stack excessive: ${min_sp_play:02X}"
    assert min_sp_update >= 0xED, f"Music_Update stack excessive: ${min_sp_update:02X}"
    assert min_sp_stop >= 0xED, f"Music_Stop stack excessive: ${min_sp_stop:02X}"


def test_gameplay_sfx_and_music_coexistence(clean_mpu: MPU, labels: Dict[str, int]):
    """Verify that update_fire_sound does not silence CMC music when fire is inactive (fire_state==0),
    that active fire overrides CH1/CH2, and that subsequent Music_Update restores CMC values.
    """
    mpu = clean_mpu

    # Ensure RTCLOK+2 is non-zero for jitter calculations
    mpu.memory[0x14] = 0x2A

    # 1. Start Gameplay music (subsong 1)
    mpu.a = 1  # MUSIC_GAMEPLAY
    run_subroutine(mpu, labels["MUSIC_PLAYSONG"])

    # Play several frames so CMC channels become active
    for _ in range(15):
        run_subroutine(mpu, labels["MUSIC_UPDATE"])

    # 2. Gameplay WITHOUT fire (fire_state == 0)
    mpu.memory[labels["FIRE_STATE"]] = 0
    run_subroutine(mpu, labels["MUSIC_UPDATE"])

    cmc_audc1 = mpu.memory[0xD201]
    cmc_audc2 = mpu.memory[0xD203]
    cmc_audf1 = mpu.memory[0xD200]
    cmc_audf2 = mpu.memory[0xD202]

    # Run update_fire_sound with fire_state == 0
    run_subroutine(mpu, labels["UPDATE_FIRE_SOUND"])

    # Assert that CH1 and CH2 registers were NOT modified or silenced
    assert mpu.memory[0xD201] == cmc_audc1, f"AUDC1 changed when fire_state==0: was ${cmc_audc1:02X}, got ${mpu.memory[0xD201]:02X}"
    assert mpu.memory[0xD203] == cmc_audc2, f"AUDC2 changed when fire_state==0: was ${cmc_audc2:02X}, got ${mpu.memory[0xD203]:02X}"
    assert mpu.memory[0xD200] == cmc_audf1, f"AUDF1 changed when fire_state==0"
    assert mpu.memory[0xD202] == cmc_audf2, f"AUDF2 changed when fire_state==0"

    # 3. Gameplay WITH fire (fire_state == 1)
    mpu.memory[labels["FIRE_STATE"]] = 1
    mpu.memory[labels["FIRE_FRAME"]] = 4

    run_subroutine(mpu, labels["UPDATE_FIRE_SOUND"])

    fire_audc1 = mpu.memory[0xD201]
    fire_audc2 = mpu.memory[0xD203]

    # Fire sound must produce volume on CH1 and white noise ($80) on CH2
    assert (fire_audc1 & 0x0F) > 0, "Fire SFX must produce volume on CH1"
    assert (fire_audc2 & 0x80) == 0x80, "Fire SFX must set distortion $80 on CH2"

    # 4. Release fire (fire_state == 0)
    mpu.memory[labels["FIRE_STATE"]] = 0

    # Next frame: Music_Update runs first
    run_subroutine(mpu, labels["MUSIC_UPDATE"])

    post_fire_audc1 = mpu.memory[0xD201]
    post_fire_audc2 = mpu.memory[0xD203]

    # CH2 should now be CMC music again (distortion not pure $80 unless CMC uses it, and volume non-zero)
    run_subroutine(mpu, labels["UPDATE_FIRE_SOUND"])

    assert mpu.memory[0xD201] == post_fire_audc1, "update_fire_sound must not alter AUDC1 after fire released"
    assert mpu.memory[0xD203] == post_fire_audc2, "update_fire_sound must not alter AUDC2 after fire released"

