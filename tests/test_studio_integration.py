import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from labirynt_studio.ui.main_window import MainWindow
from labirynt_studio.model.models import ObjectInstance
from labirynt_studio.export.atari_export import export_labyrinth_binary


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_full_studio_workflow(qapp, tmp_path):
    # 1. Inicjalizacja głównego okna z rzeczywistymi zasobami Jabberwocky
    window = MainWindow(
        objects_path="world/objects.yaml",
        colors_path="world/colors.yaml",
        charset_path="fonts/game.fnt"
    )

    # 2. Weryfikacja zasobów i stanu początkowego
    assert window.objects_lib.is_loaded is True
    assert len(window.objects_lib.objects) > 50
    assert window.palette.is_loaded is True
    assert window.charset.is_loaded is True
    assert len(window.project.screens) == 1
    assert window.project.screens[0].id == "FOREST_01"

    # 3. Dodanie obiektów na ekran FOREST_01
    screen_01 = window.project.screens[0]
    # Wybór obiektu TREE_2 (code 4)
    tree_def = window.objects_lib.get_by_code(4)
    assert tree_def is not None

    window.canvas.set_active_object(4)
    # Symulacja dodania obiektu na pozycji (0, 0)
    inst1 = ObjectInstance(code=4, x=0, y=0)
    from labirynt_studio.model.commands import AddObjectCommand
    cmd1 = AddObjectCommand(screen_01, inst1, on_change=window.canvas._on_model_changed)
    window.undo_stack.push(cmd1)

    assert len(screen_01.objects) == 1
    assert screen_01.objects[0].code == 4
    assert screen_01.objects[0].packed_xy == 0

    # Dodanie obiektu na pozycji (38, 8)
    inst2 = ObjectInstance(code=4, x=38, y=8)
    cmd2 = AddObjectCommand(screen_01, inst2, on_change=window.canvas._on_model_changed)
    window.undo_stack.push(cmd2)

    assert len(screen_01.objects) == 2
    assert screen_01.objects[1].packed_xy == (4 << 5) | 19

    # 4. Test Undo / Redo
    window.undo_stack.undo()
    assert len(screen_01.objects) == 1
    window.undo_stack.redo()
    assert len(screen_01.objects) == 2

    # 5. Utworzenie drugiego ekranu FOREST_02
    from labirynt_studio.model.models import Screen, Labyrinth
    screen_02 = Screen(id="FOREST_02", objects=[ObjectInstance(code=3, x=10, y=6)])
    window.project.add_screen(screen_02)
    window.screens_widget.refresh()
    assert len(window.project.screens) == 2

    # 6. Utworzenie labiryntu LEVEL_01
    lab = Labyrinth(id="LEVEL_01", name="Las Jabberwocky", screens=["FOREST_01", "FOREST_02"])
    window.project.labyrinths.append(lab)
    window.labyrinths_widget.refresh()
    assert len(window.project.labyrinths) == 1

    # 7. Zapis projektu do pliku YAML
    save_file = tmp_path / "project.yaml"
    from labirynt_studio.io.project_io import save_project_to_yaml, load_project_from_yaml
    ok, err = save_project_to_yaml(window.project, save_file)
    assert ok is True
    assert save_file.exists()

    # 8. Załadowanie projektu z pliku YAML do nowego okna
    new_window = MainWindow(
        project_path=str(save_file)
    )
    assert len(new_window.project.screens) == 2
    assert new_window.project.screens[0].id == "FOREST_01"
    assert len(new_window.project.screens[0].objects) == 2
    assert new_window.project.screens[1].id == "FOREST_02"
    assert len(new_window.project.screens[1].objects) == 1
    assert len(new_window.project.labyrinths) == 1
    assert new_window.project.labyrinths[0].screens == ["FOREST_01", "FOREST_02"]

    # 9. Eksport binarnego labiryntu Atari
    bin_file = tmp_path / "LEVEL_01.BIN"
    ok_bin, err_bin = export_labyrinth_binary(new_window.project, "LEVEL_01", bin_file)
    assert ok_bin is True
    assert bin_file.exists()
    
    bin_data = bin_file.read_bytes()
    # Nagłówek: 2 ekrany (bajt 0: 2)
    assert bin_data[0] == 2
    # Ekran 1: liczba obiektów = 2 (bajt 1: 2)
    assert bin_data[1] == 2
    # Ekran 1, obiekt 1: code=4, packed_xy=0 (bajty 2, 3: 4, 0)
    assert bin_data[2] == 4
    assert bin_data[3] == 0
