import sys
import pytest
from PySide6.QtWidgets import QApplication

from sprite_studio.models import Sprite, Frame
from sprite_studio.main import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_inverse_frame_operation(qapp):
    win = MainWindow()
    win._on_add_sprite()
    spr = win.current_sprite
    assert spr is not None
    assert len(spr.frames) == 1

    # Set specific pixel pattern
    pattern = [
        "10101010",
        "00000000",
        "11111111",
        "11001100",
    ] + ["00000000"] * (spr.height - 4)
    spr.frames[0].pixels = list(pattern)
    win._refresh_frame()

    # Trigger Inverse
    win._on_inverse_frame(0)

    expected = [
        "01010101",
        "11111111",
        "00000000",
        "00110011",
    ] + ["11111111"] * (spr.height - 4)

    assert spr.frames[0].pixels == expected

    # Test Undo
    win._undo()
    assert spr.frames[0].pixels == pattern

    # Test Redo
    win._redo()
    assert spr.frames[0].pixels == expected

    # Inverting again returns to original
    win._on_inverse_frame(0)
    assert spr.frames[0].pixels == pattern


def test_timeline_inverse_button_click(qapp):
    win = MainWindow()
    win._on_add_sprite()
    spr = win.current_sprite
    assert spr is not None

    spr.frames[0].pixels = ["11000011"] * spr.height
    win._refresh_frame()

    # Click the timeline's Inverse button
    win.timeline.btn_inverse.click()

    assert spr.frames[0].pixels == ["00111100"] * spr.height


def test_clear_frame_operation(qapp):
    win = MainWindow()
    win._on_add_sprite()
    spr = win.current_sprite
    assert spr is not None
    assert len(spr.frames) == 1

    pattern = ["11111111"] * spr.height
    spr.frames[0].pixels = list(pattern)
    win._refresh_frame()

    # Trigger Clear
    win._on_clear_frame(0)

    cleared = ["00000000"] * spr.height
    assert spr.frames[0].pixels == cleared

    # Test Undo
    win._undo()
    assert spr.frames[0].pixels == pattern

    # Test Redo
    win._redo()
    assert spr.frames[0].pixels == cleared


def test_timeline_clear_button_click(qapp):
    win = MainWindow()
    win._on_add_sprite()
    spr = win.current_sprite
    assert spr is not None

    spr.frames[0].pixels = ["11001100"] * spr.height
    win._refresh_frame()

    # Click the timeline's Clear button
    win.timeline.btn_clear.click()

    assert spr.frames[0].pixels == ["00000000"] * spr.height
