import subprocess
import sys
from pathlib import Path
import pytest

from labirynt_studio.model.models import Project, Screen, ObjectInstance, ObjectDefinition, ObjectSize, ObjectFlags
from labirynt_studio.io.objects_loader import ObjectsLibrary
from scripts.labirynt_builder import bake_screen_vram, SCREEN_VRAM_SIZE, generate_world_asm


def test_bake_screen_vram_accuracy():
    """Weryfikuje precyzję nakładania kafli obiektów do 440-bajtowego bufora VRAM."""
    lib = ObjectsLibrary()
    # Obiekt 2x2 na kafelkach [51, 52, 83, 84]
    obj = ObjectDefinition(
        id="TEST_TREE",
        code=4,
        size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True),
        tiles=[51, 52, 83, 84]
    )
    lib.objects.append(obj)
    lib.by_code[4] = obj

    # Umieszczamy na x=4, y=2
    screen = Screen(id="SCR_TEST", objects=[ObjectInstance(code=4, x=4, y=2)])
    vram = bake_screen_vram(screen, lib)

    assert len(vram) == SCREEN_VRAM_SIZE
    # Wiersz 2, kolumny 4, 5 -> offset = 2*40 + 4 = 84, 85
    assert vram[2 * 40 + 4] == 51
    assert vram[2 * 40 + 5] == 52
    # Wiersz 3, kolumny 4, 5 -> offset = 3*40 + 4 = 124, 125
    assert vram[3 * 40 + 4] == 83
    assert vram[3 * 40 + 5] == 84

    # Dowolny inny punkt (np. 0, 0) ma być 0
    assert vram[0] == 0
    assert vram[40] == 0


def test_labirynt_builder_cli(tmp_path):
    """Test wywołania skryptu przez CLI z parametrami."""
    out_asm = tmp_path / "test_world.asm"
    cmd = [
        sys.executable,
        "scripts/labirynt_builder.py",
        "--project", "world/project.yaml",
        "--objects", "world/objects.yaml",
        "--output", str(out_asm)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Successfully generated" in res.stdout
    assert out_asm.exists()

    content = out_asm.read_text(encoding="utf-8")
    from labirynt_studio.io.project_io import load_project_from_yaml
    proj, _ = load_project_from_yaml(Path("world/project.yaml"))
    assert f"WORLD_SCREENS_COUNT     = {len(proj.screens)}" in content
    assert "WORLD_LABYRINTHS_COUNT  = 1" in content
    assert "screen_FOREST_01_vram" in content
    assert "screen_FOREST_02_vram" in content
    assert "screen_FOREST_03_vram" in content
    assert "screens_vram_lo" in content
    assert "screens_vram_hi" in content
    assert "labyrinths_screens_lo" in content
    assert "world_color_bk      dta 0" in content
    assert "world_color_pf0     dta 20" in content
    assert "world_color_pf1     dta 24" in content
    assert "world_color_pf2     dta 194" in content
    assert "world_color_pf3     dta 130" in content


def test_missing_files_error_handling(tmp_path):
    """Test bezpiecznego wyjścia z kodem 1 przy braku plików."""
    cmd = [
        sys.executable,
        "scripts/labirynt_builder.py",
        "--project", "non_existent_project.yaml",
        "--output", str(tmp_path / "out.asm")
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "Error: Project file not found" in res.stderr


def test_custom_colors_cli(tmp_path):
    """Weryfikuje poprawne kompilowanie niestandardowych kolorów z colors.yaml."""
    colors_file = tmp_path / "custom_colors.yaml"
    colors_file.write_text("""BACKGROUND:
  atari: 14
  rgb: [0, 0, 0]
PF0:
  atari: 45
  rgb: [100, 100, 100]
PF1:
  atari: 78
  rgb: [200, 200, 200]
PF2:
  atari: 155
  rgb: [50, 150, 50]
PF3_INV:
  atari: 210
  rgb: [10, 20, 200]
""", encoding="utf-8")

    out_asm = tmp_path / "world_with_colors.asm"
    cmd = [
        sys.executable,
        "scripts/labirynt_builder.py",
        "--project", "world/project.yaml",
        "--objects", "world/objects.yaml",
        "--colors", str(colors_file),
        "--output", str(out_asm)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert out_asm.exists()

    content = out_asm.read_text(encoding="utf-8")
    assert "world_color_bk      dta 14" in content
    assert "world_color_pf0     dta 45" in content
    assert "world_color_pf1     dta 78" in content
    assert "world_color_pf2     dta 155" in content
    assert "world_color_pf3     dta 210" in content

