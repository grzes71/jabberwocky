import sys
import pytest
from PySide6.QtWidgets import QApplication

from object_studio.models import Project, ObjectDefinition
from object_studio.widgets.object_list_widget import ObjectListWidget, ORDER_CODE_OPTION, ORDER_ID_OPTION


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_object_list_widget_sorting_and_filtering(qapp):
    project = Project()
    project.available_tags = ["drzewo", "woda"]
    project.objects = [
        ObjectDefinition(id="ZEBRA", code=20, tags=["zwierze"]),
        ObjectDefinition(id="APPLE", code=50, tags=["drzewo"]),
        ObjectDefinition(id="BANANA", code=10, tags=["drzewo"]),
        ObjectDefinition(id="OCEAN", code=5, tags=["woda"]),
    ]

    widget = ObjectListWidget()
    widget.set_project(project)

    # 1. Domyślne sortowanie wg Code:
    # Oczekiwana kolejność: OCEAN (5), BANANA (10), ZEBRA (20), APPLE (50)
    assert widget.combo_order.currentText() == ORDER_CODE_OPTION
    assert widget.combo_order.currentData() == "code"
    assert len(widget.filtered_objects) == 4
    assert [o.code for o in widget.filtered_objects] == [5, 10, 20, 50]
    assert [o.id for o in widget.filtered_objects] == ["OCEAN", "BANANA", "ZEBRA", "APPLE"]

    # 2. Zmiana sortowania na ID (nazwy):
    # Oczekiwana kolejność: APPLE (50), BANANA (10), OCEAN (5), ZEBRA (20)
    idx_id = widget.combo_order.findData("id")
    assert idx_id >= 0
    widget.combo_order.setCurrentIndex(idx_id)

    assert len(widget.filtered_objects) == 4
    assert [o.id for o in widget.filtered_objects] == ["APPLE", "BANANA", "OCEAN", "ZEBRA"]
    assert [o.code for o in widget.filtered_objects] == [50, 10, 5, 20]

    # 3. Filtr tagu "drzewo" przy sortowaniu wg ID:
    # Oczekiwana kolejność: APPLE, BANANA
    idx_tag = widget.combo_tag_filter.findText("drzewo")
    assert idx_tag >= 0
    widget.combo_tag_filter.setCurrentIndex(idx_tag)

    assert len(widget.filtered_objects) == 2
    assert [o.id for o in widget.filtered_objects] == ["APPLE", "BANANA"]

    # 4. Przełączenie z powrotem na sortowanie wg Code przy aktywnym filtrze tagu:
    # Oczekiwana kolejność: BANANA (10), APPLE (50)
    idx_code = widget.combo_order.findData("code")
    widget.combo_order.setCurrentIndex(idx_code)

    assert len(widget.filtered_objects) == 2
    assert [o.id for o in widget.filtered_objects] == ["BANANA", "APPLE"]
