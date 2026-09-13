"""Unit and py65 integration tests for bottom status bar (LEVEL, SCORE, LIVES)."""

from pathlib import Path
import re
from typing import Dict, List
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


def antic_inv_to_ascii(code: int) -> str:
    """Convert an inverted ANTIC display code (with bit 7 = 1) to ASCII character."""
    assert code & 0x80, f"Expected inverted display code with bit 7 set, got {hex(code)}"
    c = code & 0x7F
    if 0 <= c <= 31:  # Space, punctuation, digits
        return chr(c + 32)
    elif 32 <= c <= 95:  # Uppercase and symbols
        return chr(c + 32)
    elif 96 <= c <= 127:  # Lowercase
        return chr(c)
    return "?"


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def labels(project_root: Path) -> Dict[str, int]:
    lab_file = project_root / "gen" / "jabberwocky.lab"
    assert lab_file.exists(), "gen/jabberwocky.lab must exist (run make all)"
    return parse_labels(lab_file)


def test_status_symbols_exist(labels: Dict[str, int]):
    """Verify that LEVEL, LIVES, SCORE, and SHOTS memory cells are defined."""
    assert "LEVEL" in labels, "LEVEL symbol not found in label table"
    assert "LIVES" in labels, "LIVES symbol not found in label table"
    assert "SCORE" in labels, "SCORE symbol not found in label table"
    assert "SHOTS" in labels, "SHOTS symbol not found in label table"
    assert "DRAW_BOTTOM_STATUS" in labels
    assert "UPDATE_BOTTOM_STATUS" in labels


def test_initial_values_in_xex(project_root: Path, labels: Dict[str, int]):
    """Verify initial memory values: LEVEL=1, LIVES=3, SCORE=4 zeroes, SHOTS=1."""
    xex_path = project_root / "jabberwocky.xex"
    memory = bytearray(65536)
    load_xex(xex_path, memory)

    level_addr = labels["LEVEL"]
    lives_addr = labels["LIVES"]
    score_addr = labels["SCORE"]
    shots_addr = labels["SHOTS"]

    assert memory[level_addr] == 1, f"LEVEL initial value should be 1, got {memory[level_addr]}"
    assert memory[lives_addr] == 3, f"LIVES initial value should be 3, got {memory[lives_addr]}"
    score_bytes = [memory[score_addr + i] for i in range(4)]
    assert score_bytes == [0, 0, 0, 0], f"SCORE initial value should be 4 zeroes, got {score_bytes}"
    assert memory[shots_addr] == 1, f"SHOTS initial value should be 1, got {memory[shots_addr]}"

    # Action screen playfield palette from world/colors.yaml
    assert memory[labels["WORLD_COLOR_BK"]] == 0
    assert memory[labels["WORLD_COLOR_PF0"]] == 20
    assert memory[labels["WORLD_COLOR_PF1"]] == 24
    assert memory[labels["WORLD_COLOR_PF2"]] == 194
    assert memory[labels["WORLD_COLOR_PF3"]] == 130


def test_draw_bottom_status_emulation(project_root: Path, labels: Dict[str, int]):
    """Emulate draw_bottom_status and verify initial display in VRAM."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_status_row1 = labels["GAME_STATUS_VRAM"] + 40

    # Clear status row with 0 before running
    for i in range(40):
        mpu.memory[vram_status_row1 + i] = 0

    # Set up return address on stack ($0100) and BRK ($00) at $0100
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DRAW_BOTTOM_STATUS"]

    steps = 0
    while mpu.pc != 0x0100 and steps < 5000:
        mpu.step()
        steps += 1

    assert mpu.pc == 0x0100, f"Routine did not return within 5000 steps, PC={hex(mpu.pc)}"

    row1_bytes = [mpu.memory[vram_status_row1 + i] for i in range(40)]
    decoded_str = "".join(antic_inv_to_ascii(b) for b in row1_bytes)

    expected = "LEVEL:01  SCORE:0000  LIVES:03  SHOTS:01"
    assert decoded_str == expected, f"VRAM row 1 mismatch:\nExpected: '{expected}'\nGot:      '{decoded_str}'"


def test_update_bottom_status_dynamic(project_root: Path, labels: Dict[str, int]):
    """Verify update_bottom_status dynamically reflects changes in LEVEL, SCORE, LIVES, SHOTS."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_status_row1 = labels["GAME_STATUS_VRAM"] + 40

    # First draw the template
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DRAW_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    # Change memory values
    level_addr = labels["LEVEL"]
    lives_addr = labels["LIVES"]
    score_addr = labels["SCORE"]
    shots_addr = labels["SHOTS"]

    mpu.memory[level_addr] = 5
    mpu.memory[lives_addr] = 2
    for i, digit in enumerate([1, 2, 3, 4]):
        mpu.memory[score_addr + i] = digit
    mpu.memory[shots_addr] = 8

    # Call update_bottom_status
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.pc = labels["UPDATE_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    row1_bytes = [mpu.memory[vram_status_row1 + i] for i in range(40)]
    decoded_str = "".join(antic_inv_to_ascii(b) for b in row1_bytes)

    expected = "LEVEL:05  SCORE:1234  LIVES:02  SHOTS:08"
    assert decoded_str == expected, f"VRAM row 1 dynamic update mismatch:\nExpected: '{expected}'\nGot:      '{decoded_str}'"


def test_bottom_bar_sprites_config(project_root: Path, labels: Dict[str, int]):
    """Verify sprite position and color memory cells for bottom status bar."""
    assert "BOT_BAR_P0_X" in labels
    assert "BOT_BAR_P1_X" in labels
    assert "BOT_BAR_P2_X" in labels
    assert "BOT_BAR_P3_X" in labels
    assert "BOT_BAR_M_X" in labels
    assert "BOT_BAR_PMG_Y" in labels
    assert "PAL_BOTTOM_P0" in labels
    assert "PAL_BOTTOM_P1" in labels
    assert "PAL_BOTTOM_P2" in labels
    assert "PAL_BOTTOM_P3" in labels
    assert "PAL_BOTTOM_M" in labels

    xex_path = project_root / "jabberwocky.xex"
    memory = bytearray(65536)
    load_xex(xex_path, memory)

    assert memory[labels["BOT_BAR_P0_X"]] == 48
    assert memory[labels["BOT_BAR_P1_X"]] == 88
    assert memory[labels["BOT_BAR_M_X"]] == 120
    assert memory[labels["BOT_BAR_P2_X"]] == 136
    assert memory[labels["BOT_BAR_P3_X"]] == 176
    assert memory[labels["BOT_BAR_PMG_Y"]] == 220

    assert memory[labels["PAL_BOTTOM_P0"]] == 0xA0  # Cyan
    assert memory[labels["PAL_BOTTOM_P1"]] == 0x90  # Blue-cyan
    assert memory[labels["PAL_BOTTOM_M"]] == 0x90   # Blue-cyan (matches SCORE)
    assert memory[labels["PAL_BOTTOM_P2"]] == 0x10  # Yellow
    assert memory[labels["PAL_BOTTOM_P3"]] == 0x20  # Fire orange


def test_dragon_energy_symbols_exist(labels: Dict[str, int]):
    """Verify that Dragon Energy bar symbols are defined."""
    assert "COUNTER_FULL" in labels
    assert "COUNTER_EIGHT" in labels
    assert "DRAGON_INITIAL_ENERGY_SEC" in labels
    assert "DRAGON_ENERGY_SEC" in labels
    assert "ENERGY_FRAMES_LO" in labels
    assert "ENERGY_FRAMES_HI" in labels
    assert "INIT_ENERGY_BAR" in labels
    assert "UPDATE_ENERGY_BAR" in labels
    assert "CALC_ENERGY_FRAMES" in labels
    assert "REASON_ENERGY_EMPTY" in labels


def test_dragon_initial_energy_values(project_root: Path, labels: Dict[str, int]):
    """Verify initial dragon energy configuration: 30 seconds flight, 40 full bar characters."""
    xex_path = project_root / "jabberwocky.xex"
    memory = bytearray(65536)
    load_xex(xex_path, memory)

    assert memory[labels["COUNTER_FULL"]] == 40
    assert memory[labels["COUNTER_EIGHT"]] == 83
    assert memory[labels["DRAGON_ENERGY_SEC"]] == 30
    assert labels["DRAGON_INITIAL_ENERGY_SEC"] == 30


def test_init_energy_bar_emulation(project_root: Path, labels: Dict[str, int]):
    """Emulate init_energy_bar: 39 chars 82 + 1 char 83 in row 0 of GAME_STATUS_VRAM."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_status_row0 = labels["GAME_STATUS_VRAM"]
    for i in range(40):
        mpu.memory[vram_status_row0 + i] = 0

    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["INIT_ENERGY_BAR"]

    steps = 0
    while mpu.pc != 0x0100 and steps < 5000:
        mpu.step()
        steps += 1

    assert mpu.pc == 0x0100
    for i in range(39):
        assert mpu.memory[vram_status_row0 + i] == 82, f"Char {i} expected 82, got {mpu.memory[vram_status_row0 + i]}"
    assert mpu.memory[vram_status_row0 + 39] == 83
    assert mpu.memory[labels["COUNTER_FULL"]] == 40
    assert mpu.memory[labels["COUNTER_EIGHT"]] == 83


def test_calc_energy_frames_emulation(project_root: Path, labels: Dict[str, int]):
    """Verify calc_energy_frames computes 1500 frames for PAL (50Hz*30s) and 1800 for NTSC (60Hz*30s)."""
    xex_path = project_root / "jabberwocky.xex"
    pal_reg = labels["PAL"]

    # Test PAL (bit 3 == 0)
    mpu_pal = MPU()
    load_xex(xex_path, mpu_pal.memory)
    mpu_pal.memory[pal_reg] = 0x01  # Bit 3 is 0 -> PAL
    mpu_pal.sp = 0xFD
    mpu_pal.stPushWord(0x0100 - 1)
    mpu_pal.memory[0x0100] = 0x00
    mpu_pal.pc = labels["CALC_ENERGY_FRAMES"]
    while mpu_pal.pc != 0x0100:
        mpu_pal.step()

    pal_frames = mpu_pal.memory[labels["ENERGY_FRAMES_LO"]] | (mpu_pal.memory[labels["ENERGY_FRAMES_HI"]] << 8)
    assert pal_frames == 1500, f"PAL 30s expected 1500 frames, got {pal_frames}"

    # Test NTSC (bit 3 == 1)
    mpu_ntsc = MPU()
    load_xex(xex_path, mpu_ntsc.memory)
    mpu_ntsc.memory[pal_reg] = 0x0E  # Bit 3 is 1 -> NTSC
    mpu_ntsc.sp = 0xFD
    mpu_ntsc.stPushWord(0x0100 - 1)
    mpu_ntsc.memory[0x0100] = 0x00
    mpu_ntsc.pc = labels["CALC_ENERGY_FRAMES"]
    while mpu_ntsc.pc != 0x0100:
        mpu_ntsc.step()

    ntsc_frames = mpu_ntsc.memory[labels["ENERGY_FRAMES_LO"]] | (mpu_ntsc.memory[labels["ENERGY_FRAMES_HI"]] << 8)
    assert ntsc_frames == 1800, f"NTSC 30s expected 1800 frames, got {ntsc_frames}"


def test_update_energy_bar_depletion_emulation(project_root: Path, labels: Dict[str, int]):
    """Verify update_energy_bar advances animation and triggers start_dragon_death on full depletion."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    # Set energy_frames to 320 for 1:1 frame-to-step test
    mpu.memory[labels["ENERGY_FRAMES_LO"]] = 320 & 0xFF
    mpu.memory[labels["ENERGY_FRAMES_HI"]] = (320 >> 8) & 0xFF
    mpu.memory[labels["GAME_OVER_REASON"]] = 0
    mpu.memory[labels["COUNTER_FULL"]] = 1
    mpu.memory[labels["COUNTER_EIGHT"]] = 90  # At edge of cycle
    mpu.memory[labels["DRAGON_DYING"]] = 0

    # Call update_energy_bar
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["UPDATE_ENERGY_BAR"]
    while mpu.pc != 0x0100:
        mpu.step()

    # COUNTER_FULL was 1 and at 90, so decrementing COUNTER_FULL reaches 0 -> death sequence starts!
    assert mpu.memory[labels["COUNTER_FULL"]] == 0
    assert mpu.memory[labels["DRAGON_DYING"]] == 1
    assert mpu.memory[labels["DEATH_TIMER"]] == 100
    # Game does not end immediately:
    assert mpu.memory[labels["GAME_OVER_REASON"]] == 0


def test_dragon_death_fade_and_movement(project_root: Path, labels: Dict[str, int]):
    """Verify update_dragon_death moves dragon towards 48 and fades luminance to 0."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    # Set up dying state
    mpu.memory[labels["DRAGON_DYING"]] = 1
    mpu.memory[labels["DRAGON_X"]] = 64
    mpu.memory[labels["DEATH_TIMER"]] = 100
    mpu.memory[labels["DEATH_MOVE_TIMER"]] = 6
    mpu.memory[labels["PAL_ACTION_DRAGON"]] = 0xC6
    mpu.memory[labels["LIVES"]] = 3

    # Step through 100 frames of fading
    for frame in range(1, 101):
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.memory[0x0100] = 0x00
        mpu.pc = labels["UPDATE_DRAGON_DEATH"]
        while mpu.pc != 0x0100:
            mpu.step()

    # At the end of 100 frames of fading:
    # 1. Dragon reached left edge (48)
    assert mpu.memory[labels["DRAGON_X"]] == 48
    # 2. Luminance reached 0 ($C0)
    assert mpu.memory[labels["PAL_ACTION_DRAGON"]] == 0xC0
    # 3. Transitioned to explosion phase (dragon_dying == 2)
    assert mpu.memory[labels["DRAGON_DYING"]] == 2
    assert mpu.memory[labels["DEATH_TIMER"]] == 24
    # 4. Lives are NOT yet decremented (explosion just started!)
    assert mpu.memory[labels["LIVES"]] == 3
    assert mpu.memory[labels["GAME_OVER_REASON"]] == 0

    # Step through 24 frames of explosion sound
    for frame in range(1, 25):
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.memory[0x0100] = 0x00
        mpu.pc = labels["UPDATE_DRAGON_DEATH"]
        while mpu.pc != 0x0100:
            mpu.step()

    # ONLY AFTER explosion completes:
    # Lives decremented from 3 to 2
    assert mpu.memory[labels["LIVES"]] == 2
    assert mpu.memory[labels["GAME_OVER_REASON"]] == 0
    # Dragon respawned:
    assert mpu.memory[labels["DRAGON_DYING"]] == 0
    assert mpu.memory[labels["DRAGON_X"]] == 64
    assert mpu.memory[labels["PAL_ACTION_DRAGON"]] == 0xC6
    assert mpu.memory[labels["COUNTER_FULL"]] == 40


def test_dragon_death_game_over_when_last_life(project_root: Path, labels: Dict[str, int]):
    """Verify update_dragon_death transitions to GAME OVER after explosion when LIVES == 1."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    # Set up explosion state on its final frame with only 1 life
    mpu.memory[labels["DRAGON_DYING"]] = 2  # DEATH_STATE_EXPLODING
    mpu.memory[labels["DRAGON_X"]] = 48
    mpu.memory[labels["DEATH_TIMER"]] = 1   # Final frame of explosion
    mpu.memory[labels["PAL_ACTION_DRAGON"]] = 0xC0
    mpu.memory[labels["LIVES"]] = 1
    mpu.memory[labels["GAME_OVER_REASON"]] = 0

    # Execute final frame of explosion
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["UPDATE_DRAGON_DEATH"]
    while mpu.pc != 0x0100:
        mpu.step()

    # Game Over triggered!
    assert mpu.memory[labels["GAME_OVER_REASON"]] == labels["REASON_LIVES_OUT"]


def test_lives_one_blinking_on_bottom_status(project_root: Path, labels: Dict[str, int]):
    """Verify LIVES digit blinks (disappears and reappears every 0.5s / 25 frames) when LIVES == 1."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_lives_digit = labels["GAME_STATUS_VRAM"] + 69

    # Initial template draw
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DRAW_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    # Set LIVES to 1
    mpu.memory[labels["LIVES"]] = 1
    mpu.memory[labels["LIVES_BLINK_TIMER"]] = 25
    mpu.memory[labels["LIVES_BLINK_STATE"]] = 0

    def step_update_status():
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.memory[0x0100] = 0x00
        mpu.pc = labels["UPDATE_BOTTOM_STATUS"]
        while mpu.pc != 0x0100:
            mpu.step()

    # Frames 1..24: '1' is visible ($91 = inverted '1')
    for _ in range(24):
        step_update_status()
        assert mpu.memory[vram_lives_digit] == 0x91, "Digit 1 should be visible during first 24 frames"

    # Frame 25 (0.5s mark): toggles to hidden ($80 = inverted space)
    step_update_status()
    assert mpu.memory[vram_lives_digit] == 0x80, "Digit 1 should disappear at 0.5s mark"

    # Frames 26..49: stays hidden
    for _ in range(24):
        step_update_status()
        assert mpu.memory[vram_lives_digit] == 0x80, "Digit 1 should remain hidden"

    # Frame 50 (1.0s mark): toggles back to visible ($91)
    step_update_status()
    assert mpu.memory[vram_lives_digit] == 0x91, "Digit 1 should reappear at 1.0s mark"

    # Change LIVES to 2: blinking stops, steady digit '2' ($92)
    mpu.memory[labels["LIVES"]] = 2
    step_update_status()
    assert mpu.memory[vram_lives_digit] == 0x92, "LIVES == 2 should display steady digit without blinking"


def test_shots_display_and_mechanic(project_root: Path, labels: Dict[str, int]):
    """Verify SHOTS values are formatted correctly as 2 digits in bottom status bar."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    vram_shots_tens = labels["GAME_STATUS_VRAM"] + 78
    vram_shots_units = labels["GAME_STATUS_VRAM"] + 79

    # Initial draw: SHOTS = 1 -> "01"
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.memory[0x0100] = 0x00
    mpu.pc = labels["DRAW_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    assert mpu.memory[vram_shots_tens] == 0x90  # '0' inverted
    assert mpu.memory[vram_shots_units] == 0x91  # '1' inverted

    # Update SHOTS to 0 -> "00"
    mpu.memory[labels["SHOTS"]] = 0
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.pc = labels["UPDATE_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    assert mpu.memory[vram_shots_tens] == 0x90  # '0' inverted
    assert mpu.memory[vram_shots_units] == 0x90  # '0' inverted

    # Update SHOTS to 15 -> "15"
    mpu.memory[labels["SHOTS"]] = 15
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.pc = labels["UPDATE_BOTTOM_STATUS"]
    while mpu.pc != 0x0100:
        mpu.step()

    assert mpu.memory[vram_shots_tens] == 0x91  # '1' inverted
    assert mpu.memory[vram_shots_units] == 0x95  # '5' inverted


def test_increase_energy_bar_emulation(project_root: Path, labels: Dict[str, int]):
    """Verify increase_energy_bar increments energy sub-steps and caps at maximum."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    status_vram = labels["GAME_STATUS_VRAM"]
    counter_full = labels["COUNTER_FULL"]
    counter_eight = labels["COUNTER_EIGHT"]
    dragon_dying = labels["DRAGON_DYING"]

    def call_increase():
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.pc = labels["INCREASE_ENERGY_BAR"]
        while mpu.pc != 0x0100:
            mpu.step()

    # 1. Start with partial energy at block 38 (0-indexed column 37), sub-step 86
    mpu.memory[counter_full] = 38
    mpu.memory[counter_eight] = 86
    mpu.memory[dragon_dying] = 0
    mpu.memory[status_vram + 37] = 86

    call_increase()
    assert mpu.memory[counter_full] == 38
    assert mpu.memory[counter_eight] == 85
    assert mpu.memory[status_vram + 37] == 85

    call_increase()
    assert mpu.memory[counter_full] == 38
    assert mpu.memory[counter_eight] == 84
    assert mpu.memory[status_vram + 37] == 84

    call_increase()
    assert mpu.memory[counter_full] == 38
    assert mpu.memory[counter_eight] == 83
    assert mpu.memory[status_vram + 37] == 83

    # 2. Block transition: from 83, it should fill block 37 with 82 and advance to block 38 at 90
    call_increase()
    assert mpu.memory[counter_full] == 39
    assert mpu.memory[counter_eight] == 90
    assert mpu.memory[status_vram + 37] == 82  # Filled previous block
    assert mpu.memory[status_vram + 38] == 90  # New end block

    # 3. Maximum energy: set to COUNTER_FULL=40, COUNTER_EIGHT=83
    mpu.memory[counter_full] = 40
    mpu.memory[counter_eight] = 83
    mpu.memory[status_vram + 39] = 83

    call_increase()
    # Stays at maximum
    assert mpu.memory[counter_full] == 40
    assert mpu.memory[counter_eight] == 83
    assert mpu.memory[status_vram + 39] == 83

    # 4. Dying sequence: should NOT increase energy
    mpu.memory[counter_full] = 30
    mpu.memory[counter_eight] = 88
    mpu.memory[dragon_dying] = 1

    call_increase()
    assert mpu.memory[counter_full] == 30
    assert mpu.memory[counter_eight] == 88


def test_check_dragon_pf3_collision_emulation(project_root: Path, labels: Dict[str, int]):
    """Verify check_dragon_collisions detects dragon_p0pf bit 3 and triggers recharge."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    dragon_p0pf = labels["DRAGON_P0PF"]
    counter_full = labels["COUNTER_FULL"]
    counter_eight = labels["COUNTER_EIGHT"]
    dragon_recharging = labels["DRAGON_RECHARGING"]
    dragon_dying = labels["DRAGON_DYING"]

    def call_check_collision():
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.pc = labels["CHECK_DRAGON_COLLISIONS"]
        while mpu.pc != 0x0100:
            mpu.step()

    # 1. No collision (dragon_p0pf = 0)
    mpu.memory[dragon_p0pf] = 0x00
    mpu.memory[counter_full] = 35
    mpu.memory[counter_eight] = 87
    mpu.memory[dragon_dying] = 0
    mpu.memory[dragon_recharging] = 1  # Should be reset to 0

    call_check_collision()
    assert mpu.memory[dragon_recharging] == 0
    assert mpu.memory[counter_eight] == 87  # No increase

    # 2. Collision with PF3 (dragon_p0pf = 0x08) -> increases energy by 1
    mpu.memory[dragon_p0pf] = 0x08
    call_check_collision()
    assert mpu.memory[dragon_recharging] == 1
    assert mpu.memory[counter_eight] == 86  # Increased from 87 to 86

    # 3. Next frame still colliding -> increases again
    mpu.memory[dragon_p0pf] = 0x08
    call_check_collision()
    assert mpu.memory[dragon_recharging] == 1
    assert mpu.memory[counter_eight] == 85  # Increased from 86 to 85

    # 4. Dying sequence with collision: should NOT recharge
    mpu.memory[dragon_dying] = 1
    mpu.memory[dragon_p0pf] = 0x08
    call_check_collision()
    assert mpu.memory[dragon_recharging] == 0
    assert mpu.memory[counter_eight] == 85  # No increase


def test_check_dragon_crash_collisions_emulation(project_root: Path, labels: Dict[str, int]):
    """Verify collision with PF0, PF1, or PF2 triggers crash death and sound."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    dragon_p0pf = labels["DRAGON_P0PF"]
    dragon_dying = labels["DRAGON_DYING"]
    death_timer = labels["DEATH_TIMER"]
    dragon_recharging = labels["DRAGON_RECHARGING"]
    scroll_speed = labels["SCROLL_SPEED"]
    audc1 = labels["AUDC1"]
    audc2 = labels["AUDC2"]

    def call_check_collision():
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.pc = labels["CHECK_DRAGON_COLLISIONS"]
        while mpu.pc != 0x0100:
            mpu.step()

    # Initialize level screens and position dragon overlapping blocking object 12 (cols 8..9, rows 0..1)
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)
    mpu.pc = labels["INIT_LEVEL_SCREENS"]
    while mpu.pc != 0x0100:
        mpu.step()
    mpu.memory[labels["DRAGON_Y"]] = 40

    # Test collision with each playfield color (PF0 = 0x01, PF1 = 0x02, PF2 = 0x04)
    for mask in (0x01, 0x02, 0x04, 0x09):  # 0x09 is PF0 + PF3 (crash takes priority)
        mpu.memory[dragon_dying] = 0
        mpu.memory[death_timer] = 0
        mpu.memory[dragon_recharging] = 1
        mpu.memory[scroll_speed] = 0xC0
        mpu.memory[dragon_p0pf] = mask

        call_check_collision()

        # Dragon should enter crash state (DEATH_STATE_CRASH = 3)
        assert mpu.memory[dragon_dying] == 3
        assert mpu.memory[death_timer] == 24  # CRASH_DURATION
        assert mpu.memory[dragon_recharging] == 0  # Recharging canceled
        assert mpu.memory[scroll_speed] == 0       # Momentum halted
        assert mpu.memory[audc1] == 0x2F           # Frame 0 crash sound on Ch 1
        assert mpu.memory[audc2] == 0x8F           # Frame 0 crash sound on Ch 2


def test_dragon_crash_death_sequence_and_sound_emulation(project_root: Path, labels: Dict[str, int]):
    """Verify update_dragon_death plays crash sound over 24 frames and decrements life."""
    xex_path = project_root / "jabberwocky.xex"
    mpu = MPU()
    load_xex(xex_path, mpu.memory)

    dragon_dying = labels["DRAGON_DYING"]
    death_timer = labels["DEATH_TIMER"]
    lives = labels["LIVES"]
    game_over_reason = labels["GAME_OVER_REASON"]
    audc1 = labels["AUDC1"]
    audc2 = labels["AUDC2"]

    def call_update_death():
        mpu.sp = 0xFD
        mpu.stPushWord(0x0100 - 1)
        mpu.pc = labels["UPDATE_DRAGON_DEATH"]
        while mpu.pc != 0x0100:
            mpu.step()

    # Setup crash state with 3 lives
    mpu.memory[dragon_dying] = 3  # DEATH_STATE_CRASH
    mpu.memory[death_timer] = 24
    mpu.memory[lives] = 3
    mpu.memory[game_over_reason] = 0

    # Step through 23 frames of crash
    for frame in range(23):
        call_update_death()
        assert mpu.memory[dragon_dying] == 3
        assert mpu.memory[death_timer] == 23 - frame

    # Step final 24th frame (crash finishes)
    call_update_death()

    # POKEY should be silenced
    assert mpu.memory[audc1] == 0
    assert mpu.memory[audc2] == 0

    # Lives decremented from 3 to 2, dragon respawned (dying = 0)
    assert mpu.memory[lives] == 2
    assert mpu.memory[dragon_dying] == 0
    assert mpu.memory[game_over_reason] == 0

    # Now test crash with 1 life -> Game Over
    mpu.memory[dragon_dying] = 3
    mpu.memory[death_timer] = 1
    mpu.memory[lives] = 1
    mpu.memory[game_over_reason] = 0

    call_update_death()
    assert mpu.memory[game_over_reason] == labels["REASON_LIVES_OUT"]








