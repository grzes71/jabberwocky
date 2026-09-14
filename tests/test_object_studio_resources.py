import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from object_studio.main import MainWindow, parse_args
from object_studio.widgets.resource_dialog import ResourceDialog
from object_studio.settings import DEFAULT_COLORS


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture(autouse=True)
def isolate_settings_and_colors(monkeypatch):
    fake_storage = {}

    class FakeSettings:
        def __init__(self, *args, **kwargs):
            pass

        def value(self, key, default=None, type=None):
            val = fake_storage.get(key, default)
            return type(val) if type and val is not None else val

        def setValue(self, key, value):
            fake_storage[key] = value

    monkeypatch.setattr("object_studio.main.QSettings", FakeSettings)

    orig_colors = dict(DEFAULT_COLORS)
    yield
    DEFAULT_COLORS.clear()
    DEFAULT_COLORS.update(orig_colors)


def test_resource_dialog_get_paths(qapp):
    dlg = ResourceDialog(
        objects_path="world/objects.yaml",
        colors_path="world/colors.yaml",
        charset_path="fonts/game.fnt"
    )
    assert dlg.get_paths() == ("world/objects.yaml", "world/colors.yaml", "fonts/game.fnt")


def test_resource_dialog_validation_non_existent(qapp, monkeypatch):
    dlg = ResourceDialog(
        objects_path="invalid/path/to/objects.yaml",
        colors_path="invalid/colors.yaml",
        charset_path="invalid/game.fnt"
    )
    warning_called = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, msg: warning_called.append(msg))

    dlg._validate_and_accept()
    assert len(warning_called) == 1
    assert "Nie odnaleziono" in warning_called[0]


def test_resource_dialog_validation_success(qapp):
    dlg = ResourceDialog(
        objects_path="world/objects.yaml",
        colors_path="world/colors.yaml",
        charset_path="fonts/game.fnt"
    )
    accepted = []
    dlg.accept = lambda: accepted.append(True)
    dlg._validate_and_accept()
    assert accepted == [True]


def test_object_studio_main_window_loads_resources(qapp):
    window = MainWindow(
        objects_path="world/objects.yaml",
        colors_path="world/colors.yaml",
        charset_path="fonts/game.fnt"
    )

    # Weryfikacja załadowania obiektów
    assert window.project is not None
    assert len(window.project.objects) > 0
    assert window.current_object is not None

    # Weryfikacja załadowania charsetu
    assert window.charset is not None
    assert len(window.charset.data) == 1024

    # Weryfikacja załadowania kolorów z colors.yaml
    assert DEFAULT_COLORS["BACKGROUND"] == (0, 0, 0)
    assert DEFAULT_COLORS["PF0"] == (140, 70, 0)
    assert DEFAULT_COLORS["PF1"] == (236, 130, 0)
    assert DEFAULT_COLORS["PF2"] == (0, 85, 0)
    assert DEFAULT_COLORS["PF3_INV"] == (0, 0, 176)


def test_object_studio_load_resources_reload(qapp, tmp_path):
    # Utwórz tymczasowy plik colors.yaml z unikalnymi kolorami
    custom_colors = tmp_path / "custom_colors.yaml"
    custom_colors.write_text(
        "BACKGROUND:\n  rgb: [10, 20, 30]\nPF0:\n  rgb: [40, 50, 60]\n",
        encoding="utf-8"
    )

    window = MainWindow(
        objects_path="world/objects.yaml",
        colors_path="world/colors.yaml",
        charset_path="fonts/game.fnt"
    )

    # Przeładuj z nowym plikiem kolorów
    ok = window.load_resources(
        objects_path="world/objects.yaml",
        colors_path=str(custom_colors),
        charset_path="fonts/game.fnt"
    )
    assert ok is True
    assert DEFAULT_COLORS["BACKGROUND"] == (10, 20, 30)
    assert DEFAULT_COLORS["PF0"] == (40, 50, 60)


def test_parse_args(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["object_studio.main", "--objects", "custom_obj.yaml", "--colors", "custom_col.yaml", "--charset", "custom_chr.fnt"]
    )
    args = parse_args()
    assert args.objects == "custom_obj.yaml"
    assert args.colors == "custom_col.yaml"
    assert args.charset == "custom_chr.fnt"
