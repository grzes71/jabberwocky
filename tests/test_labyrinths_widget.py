"""Unit tests for LabyrinthDialog and level name editing in LabyrinthsWidget."""

import sys
import pytest
from PySide6.QtWidgets import QApplication, QDialog

from labirynt_studio.model.models import Project, Labyrinth
from labirynt_studio.ui.labyrinths_widget import LabyrinthsWidget, LabyrinthDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_labyrinth_dialog_data_and_validation(qapp, monkeypatch):
    """Test LabyrinthDialog data retrieval and validation."""
    monkeypatch.setattr("labirynt_studio.ui.labyrinths_widget.QMessageBox.warning", lambda *args, **kwargs: None)
    existing_ids = {"LEVEL_01", "LEVEL_02"}
    dlg = LabyrinthDialog(
        lab_id="LEVEL_01",
        lab_name="Tulgey Forest",
        existing_ids=existing_ids,
        is_new=False,
    )
    assert dlg.id_edit.text() == "LEVEL_01"
    assert dlg.name_edit.text() == "Tulgey Forest"

    # Modify name
    dlg.name_edit.setText("Dark Woods")
    new_id, new_name = dlg.get_data()
    assert new_id == "LEVEL_01"
    assert new_name == "Dark Woods"

    # Test validation: empty ID
    dlg.id_edit.setText("   ")
    dlg._validate_and_accept()
    assert dlg.result() != QDialog.DialogCode.Accepted

    # Test validation: duplicate ID
    dlg.id_edit.setText("LEVEL_02")
    dlg._validate_and_accept()
    assert dlg.result() != QDialog.DialogCode.Accepted

    # Test validation: valid new ID
    dlg.id_edit.setText("LEVEL_03")
    dlg._validate_and_accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    assert dlg.get_data() == ("LEVEL_03", "Dark Woods")


def test_labyrinths_widget_displays_level_name(qapp):
    """Test that LabyrinthsWidget displays formatted ID and level name."""
    project = Project(
        name="Test",
        labyrinths=[
            Labyrinth(id="LEVEL_01", name="Tulgey Forest", screens=[]),
            Labyrinth(id="LEVEL_02", name="", screens=[]),
        ],
    )
    widget = LabyrinthsWidget(project)

    assert widget.lab_list.count() == 2
    assert widget.lab_list.item(0).text() == "LEVEL_01 (Tulgey Forest)"
    assert widget.lab_list.item(1).text() == "LEVEL_02"


def test_labyrinths_widget_rename_labyrinth(qapp, monkeypatch):
    """Test renaming a labyrinth level name updates model and UI."""
    project = Project(
        name="Test",
        labyrinths=[
            Labyrinth(id="LEVEL_01", name="Tulgey Forest", screens=[]),
        ],
    )
    widget = LabyrinthsWidget(project)
    widget.lab_list.setCurrentRow(0)

    # Mock LabyrinthDialog.exec to simulate user entering new name
    def mock_exec(self):
        self.name_edit.setText("Jabberwock Lair")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(LabyrinthDialog, "exec", mock_exec)

    changed_called = []
    widget.labyrinths_changed.connect(lambda: changed_called.append(True))

    widget._rename_labyrinth()

    assert project.labyrinths[0].name == "Jabberwock Lair"
    assert widget.lab_list.item(0).text() == "LEVEL_01 (Jabberwock Lair)"
    assert len(changed_called) == 1


def test_labyrinths_widget_create_labyrinth_with_name(qapp, monkeypatch):
    """Test creating a new labyrinth with level name via LabyrinthDialog."""
    project = Project(
        name="Test",
        labyrinths=[
            Labyrinth(id="LEVEL_01", name="Tulgey Forest", screens=[]),
        ],
    )
    widget = LabyrinthsWidget(project)

    def mock_exec(self):
        self.id_edit.setText("LEVEL_02")
        self.name_edit.setText("Snark Caverns")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(LabyrinthDialog, "exec", mock_exec)

    changed_called = []
    widget.labyrinths_changed.connect(lambda: changed_called.append(True))

    widget._create_labyrinth()

    assert len(project.labyrinths) == 2
    assert project.labyrinths[1].id == "LEVEL_02"
    assert project.labyrinths[1].name == "Snark Caverns"
    assert widget.lab_list.item(1).text() == "LEVEL_02 (Snark Caverns)"
    assert len(changed_called) == 1


def test_labyrinths_widget_move_up_down(qapp):
    """Test reordering labyrinths up and down updates project list, UI, and emits signal."""
    project = Project(
        name="Test",
        labyrinths=[
            Labyrinth(id="LEVEL_01", name="Poziom 1", screens=[]),
            Labyrinth(id="LEVEL_02", name="Poziom 2", screens=[]),
            Labyrinth(id="LEVEL_03", name="Poziom 3", screens=[]),
        ],
    )
    widget = LabyrinthsWidget(project)

    changed_events = []
    widget.labyrinths_changed.connect(lambda: changed_events.append(True))

    # Select LEVEL_02 (row 1) and move UP
    widget.lab_list.setCurrentRow(1)
    widget._move_labyrinth_up()

    assert [l.id for l in project.labyrinths] == ["LEVEL_02", "LEVEL_01", "LEVEL_03"]
    assert widget.lab_list.currentRow() == 0
    assert len(changed_events) == 1

    # Moving UP when already at top (row 0) should do nothing
    widget._move_labyrinth_up()
    assert [l.id for l in project.labyrinths] == ["LEVEL_02", "LEVEL_01", "LEVEL_03"]
    assert len(changed_events) == 1

    # Move LEVEL_02 DOWN
    widget._move_labyrinth_down()
    assert [l.id for l in project.labyrinths] == ["LEVEL_01", "LEVEL_02", "LEVEL_03"]
    assert widget.lab_list.currentRow() == 1
    assert len(changed_events) == 2

    # Move LEVEL_02 DOWN again
    widget._move_labyrinth_down()
    assert [l.id for l in project.labyrinths] == ["LEVEL_01", "LEVEL_03", "LEVEL_02"]
    assert widget.lab_list.currentRow() == 2
    assert len(changed_events) == 3

    # Moving DOWN when at bottom (row 2) should do nothing
    widget._move_labyrinth_down()
    assert [l.id for l in project.labyrinths] == ["LEVEL_01", "LEVEL_03", "LEVEL_02"]
    assert len(changed_events) == 3

