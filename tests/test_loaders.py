from pathlib import Path
import pytest
import sys
from PySide6.QtWidgets import QApplication

from labirynt_studio.rendering.charset import Charset
from labirynt_studio.rendering.palette import AtariPalette
from labirynt_studio.rendering.renderer import AtariRenderer
from labirynt_studio.io.objects_loader import ObjectsLibrary

# Uruchomienie minimalnej instancji QApplication dla testów graficznych headless
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_load_real_charset():
    fnt_path = Path("fonts/game.fnt")
    assert fnt_path.exists(), "fonts/game.fnt powinien istnieć w projekcie"
    
    charset = Charset()
    loaded = charset.load(fnt_path)
    assert loaded is True
    assert charset.is_loaded is True
    assert len(charset.data) == 1024

    # Test pobrania pikseli znaku (np. znak 0 i znak 128 - inwersja)
    pixels_0 = charset.get_tile_pixels(0)
    assert len(pixels_0) == 8
    assert len(pixels_0[0]) == 4

    pixels_inv = charset.get_tile_pixels(130)
    assert len(pixels_inv) == 8


def test_load_real_colors():
    colors_path = Path("world/colors.yaml")
    assert colors_path.exists(), "world/colors.yaml powinien istnieć w projekcie"

    pal = AtariPalette()
    loaded = pal.load(colors_path)
    assert loaded is True
    assert pal.is_loaded is True
    assert pal.raw_rgb["BACKGROUND"] == (0, 0, 0)
    assert pal.raw_rgb["PF0"] == (140, 70, 0)
    assert pal.raw_rgb["PF1"] == (236, 130, 0)
    assert pal.raw_rgb["PF2"] == (0, 85, 0)
    assert pal.raw_rgb["PF3_INV"] == (0, 0, 176)


def test_load_real_objects():
    obj_path = Path("world/objects.yaml")
    assert obj_path.exists(), "world/objects.yaml powinien istnieć w projekcie"

    lib = ObjectsLibrary()
    loaded = lib.load(obj_path)
    assert loaded is True
    assert lib.is_loaded is True
    assert len(lib.objects) > 50
    assert "woda" in lib.tags
    assert "drzewo" in lib.tags

    # TREE_2 o kodzie 4
    tree = lib.get_by_code(4)
    assert tree is not None
    assert tree.id == "TREE_2"
    assert tree.size.width == 2
    assert tree.size.height == 2
    assert tree.tiles == [51, 52, 83, 84]


def test_rendering_engine(qapp):
    charset = Charset()
    charset.load("fonts/game.fnt")
    pal = AtariPalette()
    pal.load("world/colors.yaml")
    lib = ObjectsLibrary()
    lib.load("world/objects.yaml")

    renderer = AtariRenderer(charset, pal)

    # Renderowanie pojedynczego kafelka
    img = renderer.render_tile_image(51)
    assert img.width() == 8
    assert img.height() == 8

    # Renderowanie obiektu TREE_2 (2x2 znaki -> 16x16 px)
    tree = lib.get_by_code(4)
    assert tree is not None
    tree_img = renderer.render_object_image(tree)
    assert tree_img.width() == 16
    assert tree_img.height() == 16
