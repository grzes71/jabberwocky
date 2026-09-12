import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QUndoStack, QMouseEvent
from PySide6.QtCore import Qt, QPointF

from labirynt_studio.io.objects_loader import ObjectsLibrary
from labirynt_studio.rendering.palette import AtariPalette
from labirynt_studio.rendering.charset import Charset
from labirynt_studio.rendering.renderer import AtariRenderer
from labirynt_studio.model.models import Screen, ObjectInstance
from labirynt_studio.ui.canvas_view import CanvasView
from labirynt_studio.rendering.renderer import CHAR_PIXEL_WIDTH, CHAR_PIXEL_HEIGHT


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def objects_lib():
    lib = ObjectsLibrary()
    lib.load("world/objects.yaml")
    return lib


@pytest.fixture
def canvas(qapp, objects_lib):
    palette = AtariPalette()
    palette.load("world/colors.yaml")
    charset = Charset()
    charset.load("fonts/game.fnt")
    renderer = AtariRenderer(charset, palette)
    undo_stack = QUndoStack()
    c = CanvasView(renderer, objects_lib, undo_stack)
    return c


def test_screen_overlap_logic(objects_lib):
    screen = Screen(id="TEST")
    # Tree 2 (code 4) is 2x2. Place at (4, 4) -> covers x: [4, 5], y: [4, 5]
    inst = ObjectInstance(code=4, x=4, y=4)
    screen.objects.append(inst)

    # 1. Adjacent objects touching boundaries (no overlap)
    # Right adjacent: (6, 4), 2x2 -> covers x: [6, 7], y: [4, 5]
    assert screen.can_place_object(6, 4, 2, 2, objects_lib.by_code) is True
    # Left adjacent: (2, 4), 2x2 -> covers x: [2, 3], y: [4, 5]
    assert screen.can_place_object(2, 4, 2, 2, objects_lib.by_code) is True
    # Bottom adjacent: (4, 6), 2x2 -> covers x: [4, 5], y: [6, 7]
    assert screen.can_place_object(4, 6, 2, 2, objects_lib.by_code) is True
    # Top adjacent: (4, 2), 2x2 -> covers x: [4, 5], y: [2, 3]
    assert screen.can_place_object(4, 2, 2, 2, objects_lib.by_code) is True

    # 2. Exact overlap
    assert screen.can_place_object(4, 4, 2, 2, objects_lib.by_code) is False
    assert screen.get_overlapping_object(4, 4, 2, 2, objects_lib.by_code) == inst

    # 3. Partial overlap
    # Sharing 1 column: (5, 4), 2x2
    assert screen.can_place_object(5, 4, 2, 2, objects_lib.by_code) is False
    # Sharing 1 row: (4, 5), 2x2
    assert screen.can_place_object(4, 5, 2, 2, objects_lib.by_code) is False

    # 4. Large object enclosing: PALM_SWAMP (code 6, 4x3) placed at (2, 3) covers x: [2, 5], y: [3, 5]
    assert screen.can_place_object(2, 3, 4, 3, objects_lib.by_code) is False

    # 5. Out of bounds
    assert screen.can_place_object(-2, 0, 2, 2, objects_lib.by_code) is False
    assert screen.can_place_object(39, 0, 2, 2, objects_lib.by_code) is False
    assert screen.can_place_object(0, 10, 2, 2, objects_lib.by_code) is False

    # 6. Exclude parameter (e.g. self-check during move)
    assert screen.can_place_object(4, 4, 2, 2, objects_lib.by_code, exclude=inst) is True


def test_canvas_prevents_placing_object_on_occupied_space(canvas):
    screen = Screen(id="SCR1")
    canvas.set_screen(screen)
    canvas.set_active_object(4)  # TREE_2 (2x2)

    messages = []
    canvas.status_message_requested.connect(messages.append)

    # Oblicz pozycję pikselową dla (x=4, y=4)
    px = 4 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py = 4 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2

    # 1. Postawienie pierwszego obiektu
    event1 = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px, py),
        QPointF(px, py),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(event1)

    assert len(screen.objects) == 1
    assert screen.objects[0].x == 4
    assert screen.objects[0].y == 4

    # 2. Próba postawienia drugiego obiektu w tym samym miejscu
    event2 = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px, py),
        QPointF(px, py),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(event2)

    # Obiekt NIE został dodany!
    assert len(screen.objects) == 1
    assert len(messages) == 1
    assert "zajęty" in messages[-1]

    # 3. Próba postawienia częściowo nachodzącego (np. z przesunięciem o 1 kafelek siatki niekolizyjnej)
    # Na pozycji x=8, y=4 (miejsce wolne)
    px_free = 8 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py_free = 4 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2
    event3 = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px_free, py_free),
        QPointF(px_free, py_free),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(event3)

    assert len(screen.objects) == 2
    assert screen.objects[1].x == 8
    assert screen.objects[1].y == 4


def test_canvas_prevents_drag_and_drop_onto_occupied_space(canvas):
    screen = Screen(id="SCR_DRAG")
    inst1 = ObjectInstance(code=4, x=4, y=4)
    inst2 = ObjectInstance(code=4, x=10, y=4)
    screen.objects.extend([inst1, inst2])
    canvas.set_screen(screen)
    canvas.set_tool_mode("MOVE")

    messages = []
    canvas.status_message_requested.connect(messages.append)

    # Chwyć inst2 na (10, 4)
    px_inst2 = 10 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py_inst2 = 4 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px_inst2, py_inst2),
        QPointF(px_inst2, py_inst2),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_event)
    assert canvas.is_dragging is True
    assert canvas.selected_instance == inst2

    # Przeciągnij na (4, 4) gdzie stoi inst1
    px_inst1 = 4 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py_inst1 = 4 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2

    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(px_inst1, py_inst1),
        QPointF(px_inst1, py_inst1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseMoveEvent(move_event)
    assert inst2.x == 4
    assert inst2.y == 4

    # Puść przycisk myszy
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(px_inst1, py_inst1),
        QPointF(px_inst1, py_inst1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseReleaseEvent(release_event)

    # Przesunięcie powinno zostać odrzucone i inst2 powinno wrócić na (10, 4)
    assert inst2.x == 10
    assert inst2.y == 4
    assert len(messages) == 1
    assert "docelowy obszar pokrywa się" in messages[-1]


def test_canvas_prevents_paste_onto_occupied_space(canvas):
    screen = Screen(id="SCR_PASTE")
    inst1 = ObjectInstance(code=4, x=4, y=4)
    screen.objects.append(inst1)
    canvas.set_screen(screen)
    canvas.set_active_object(None)

    canvas.clipboard_instance = ObjectInstance(code=4, x=4, y=4)

    messages = []
    canvas.status_message_requested.connect(messages.append)

    # Ustaw kursor hover nad (4, 4)
    canvas.is_mouse_over = True
    canvas.hover_char_x = 4
    canvas.hover_char_y = 4

    canvas.paste_selected()

    # Wklejenie zablokowane
    assert len(screen.objects) == 1
    assert len(messages) == 1
    assert "zajęty" in messages[-1]

    # Ustaw kursor hover nad wolnym miejscem (14, 4)
    canvas.hover_char_x = 14
    canvas.hover_char_y = 4
    canvas.paste_selected()

    # Wklejenie powiodło się
    assert len(screen.objects) == 2
    assert screen.objects[1].x == 14
    assert screen.objects[1].y == 4


def test_canvas_tool_modes_distinction(canvas):
    screen = Screen(id="SCR_MODES")
    inst1 = ObjectInstance(code=4, x=4, y=4)
    screen.objects.append(inst1)
    canvas.set_screen(screen)

    # 1. Domyślny tryb to INSERT
    assert canvas.tool_mode == "INSERT"
    canvas.set_active_object(4)

    # W trybie INSERT kliknięcie na istniejący obiekt nie przeciąga go,
    # tylko próbuje postawić obiekt (i zostaje odrzucone przez regułę niepokrywania)
    px_inst1 = 4 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py_inst1 = 4 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px_inst1, py_inst1),
        QPointF(px_inst1, py_inst1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_event)
    assert canvas.is_dragging is False
    assert len(screen.objects) == 1

    # W trybie INSERT kliknięcie na wolne miejsce (12, 6) wstawia obiekt
    px_free = 12 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py_free = 6 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2
    press_free = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px_free, py_free),
        QPointF(px_free, py_free),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_free)
    assert len(screen.objects) == 2
    assert screen.objects[1].x == 12
    assert screen.objects[1].y == 6

    # 2. Przełączenie do trybu MOVE
    canvas.set_tool_mode("MOVE")
    assert canvas.tool_mode == "MOVE"

    # W trybie MOVE kliknięcie na wolne miejsce NIE wstawia obiektu
    px_free2 = 20 * CHAR_PIXEL_WIDTH * canvas.zoom + 2
    py_free2 = 6 * CHAR_PIXEL_HEIGHT * canvas.zoom + 2
    press_free2 = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(px_free2, py_free2),
        QPointF(px_free2, py_free2),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_free2)
    assert len(screen.objects) == 2

    # W trybie MOVE kliknięcie na obiekt inst1 rozpoczyna przeciąganie
    canvas.mousePressEvent(press_event)
    assert canvas.is_dragging is True
    assert canvas.selected_instance == inst1


def test_main_window_tool_modes(qapp):
    from labirynt_studio.ui.main_window import MainWindow
    window = MainWindow(
        objects_path="world/objects.yaml",
        colors_path="world/colors.yaml",
        charset_path="fonts/game.fnt"
    )

    # Początkowy stan: INSERT
    assert window.canvas.tool_mode == "INSERT"
    assert window.act_tool_insert.isChecked() is True
    assert window.act_tool_move.isChecked() is False
    assert window.tool_combo.currentData() == "INSERT"
    assert "Wstawianie" in window.status_tool_label.text()

    # Zmiana trybu na MOVE przez akcję
    window.act_tool_move.trigger()
    assert window.canvas.tool_mode == "MOVE"
    assert window.act_tool_insert.isChecked() is False
    assert window.act_tool_move.isChecked() is True
    assert window.tool_combo.currentData() == "MOVE"
    assert "Przesuwanie" in window.status_tool_label.text()

    # Wybór obiektu z palety automatycznie przełącza na INSERT
    window._on_palette_object_selected(4)
    assert window.canvas.tool_mode == "INSERT"
    assert window.act_tool_insert.isChecked() is True
    assert window.tool_combo.currentData() == "INSERT"
    assert "Wstawianie" in window.status_tool_label.text()

