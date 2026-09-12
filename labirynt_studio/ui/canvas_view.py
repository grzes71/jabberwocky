"""Interaktywne płótno edytora ekranu 40x11 ze snapem do siatki 2x2, podglądem DESIGN / ATARI i operacjami myszy."""

from typing import Optional, List, Tuple
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QMouseEvent, QKeyEvent, 
    QUndoStack, QImage, QPixmap, QAction
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint

from ..rendering.renderer import (
    AtariRenderer, CHAR_PIXEL_WIDTH, CHAR_PIXEL_HEIGHT,
    SCREEN_WIDTH_CHARS, SCREEN_HEIGHT_CHARS,
    SCREEN_WIDTH_PIXELS, SCREEN_HEIGHT_PIXELS
)
from ..rendering.charset import Charset
from ..rendering.palette import AtariPalette
from ..io.objects_loader import ObjectsLibrary
from ..model.models import Screen, ObjectInstance, ObjectDefinition
from ..model.packing import snap_coordinate, GRID_STEP_X, GRID_STEP_Y
from ..model.commands import AddObjectCommand, RemoveObjectCommand, MoveObjectCommand, PasteObjectsCommand


class CanvasView(QWidget):
    screen_modified = Signal()
    cursor_position_changed = Signal(int, int)  # x, y w znakach
    selection_changed = Signal(object)          # ObjectInstance lub None
    status_message_requested = Signal(str)
    tool_mode_changed = Signal(str)             # "INSERT" lub "MOVE"

    def __init__(
        self,
        renderer: AtariRenderer,
        objects_lib: ObjectsLibrary,
        undo_stack: QUndoStack,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.renderer = renderer
        self.objects_lib = objects_lib
        self.undo_stack = undo_stack

        self.current_screen: Optional[Screen] = None
        self.zoom: int = 4
        self.mode: str = "DESIGN"       # "DESIGN" lub "ATARI"
        self.tool_mode: str = "INSERT"  # "INSERT" (wstawianie) lub "MOVE" (przesuwanie)

        self.active_object_code: Optional[int] = None
        self.selected_instance: Optional[ObjectInstance] = None

        # Stan interakcji myszy
        self.hover_char_x: int = 0
        self.hover_char_y: int = 0
        self.is_mouse_over: bool = False
        
        self.is_dragging: bool = False
        self.drag_start_x: int = 0
        self.drag_start_y: int = 0
        self.drag_orig_inst_x: int = 0
        self.drag_orig_inst_y: int = 0

        # Schowek dla Copy/Paste
        self.clipboard_instance: Optional[ObjectInstance] = None

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._update_size()

    def set_tool_mode(self, mode: str):
        """Ustawia tryb narzędzia: 'INSERT' (wstawianie obiektów) lub 'MOVE' (przesuwanie obiektów)."""
        if mode in ("INSERT", "MOVE"):
            self.tool_mode = mode
            if self.is_dragging and mode != "MOVE":
                self.is_dragging = False
                if self.selected_instance:
                    self.selected_instance.x = self.drag_orig_inst_x
                    self.selected_instance.y = self.drag_orig_inst_y
            self._update_cursor()
            self.tool_mode_changed.emit(mode)
            self.update()

    def _update_cursor(self, raw_cx: Optional[int] = None, raw_cy: Optional[int] = None):
        """Aktualizuje kursor myszy w zależności od trybu pracy i pozycji nad obiektem."""
        if self.tool_mode == "INSERT":
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif self.tool_mode == "MOVE":
            if self.is_dragging:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                if self.current_screen and raw_cx is not None and raw_cy is not None:
                    hit = self.current_screen.get_object_at(raw_cx, raw_cy, self.objects_lib.by_code)
                    if hit:
                        self.setCursor(Qt.CursorShape.OpenHandCursor)
                        return
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_screen(self, screen: Optional[Screen]):
        self.current_screen = screen
        self.selected_instance = None
        self.selection_changed.emit(None)
        self.update()

    def set_zoom(self, zoom: int):
        self.zoom = max(1, zoom)
        self._update_size()
        self.update()

    def set_mode(self, mode: str):
        if mode in ("DESIGN", "ATARI"):
            self.mode = mode
            self.update()

    def set_active_object(self, code: Optional[int]):
        self.active_object_code = code
        self.update()

    def _update_size(self):
        w = SCREEN_WIDTH_PIXELS * self.zoom
        h = SCREEN_HEIGHT_PIXELS * self.zoom
        self.setFixedSize(w, h)

    def _px_to_char_coord(self, px_x: float, px_y: float) -> Tuple[int, int]:
        """Konwertuje piksele widżetu na współrzędne znakowe (0..39, 0..10) zaokrąglone do siatki 2x2."""
        char_w = CHAR_PIXEL_WIDTH * self.zoom
        char_h = CHAR_PIXEL_HEIGHT * self.zoom
        
        cx = int(px_x // char_w)
        cy = int(px_y // char_h)

        # Snap do 2x2
        snap_x = (cx // GRID_STEP_X) * GRID_STEP_X
        snap_y = (cy // GRID_STEP_Y) * GRID_STEP_Y

        snap_x = max(0, min(snap_x, SCREEN_WIDTH_CHARS - GRID_STEP_X))
        snap_y = max(0, min(snap_y, SCREEN_HEIGHT_CHARS - 1))
        # Wyrównaj snap_y do wielokrotności 2
        snap_y = (snap_y // GRID_STEP_Y) * GRID_STEP_Y

        return snap_x, snap_y

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        self.is_mouse_over = True
        snap_x, snap_y = self._px_to_char_coord(pos.x(), pos.y())

        char_w = CHAR_PIXEL_WIDTH * self.zoom
        char_h = CHAR_PIXEL_HEIGHT * self.zoom
        raw_cx = int(pos.x() // char_w)
        raw_cy = int(pos.y() // char_h)

        if self.tool_mode == "MOVE" and not self.is_dragging:
            self._update_cursor(raw_cx, raw_cy)

        if snap_x != self.hover_char_x or snap_y != self.hover_char_y:
            self.hover_char_x = snap_x
            self.hover_char_y = snap_y
            self.cursor_position_changed.emit(snap_x, snap_y)
            
            if self.tool_mode == "MOVE" and self.is_dragging and self.selected_instance and self.current_screen:
                # Oblicz nową pozycję podczas przeciągania
                dx = snap_x - self.drag_start_x
                dy = snap_y - self.drag_start_y
                cand_x = max(0, min(self.drag_orig_inst_x + dx, SCREEN_WIDTH_CHARS - GRID_STEP_X))
                cand_y = max(0, min(self.drag_orig_inst_y + dy, SCREEN_HEIGHT_CHARS - 1))
                cand_x = (cand_x // GRID_STEP_X) * GRID_STEP_X
                cand_y = (cand_y // GRID_STEP_Y) * GRID_STEP_Y
                self.selected_instance.x = cand_x
                self.selected_instance.y = cand_y

            self.update()

    def leaveEvent(self, event):
        self.is_mouse_over = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if not self.current_screen:
            return

        pos = event.position()
        snap_x, snap_y = self._px_to_char_coord(pos.x(), pos.y())

        # Dokładna pozycja znaku pod kursorem (niezsnapowana) do selekcji obiektu
        char_w = CHAR_PIXEL_WIDTH * self.zoom
        char_h = CHAR_PIXEL_HEIGHT * self.zoom
        raw_cx = int(pos.x() // char_w)
        raw_cy = int(pos.y() // char_h)

        hit = self.current_screen.get_object_at(raw_cx, raw_cy, self.objects_lib.by_code)

        if event.button() == Qt.MouseButton.LeftButton:
            if self.tool_mode == "INSERT":
                # Tryb 1: Wstawianie obiektów (domyślny)
                if self.active_object_code is not None:
                    obj_def = self.objects_lib.get_by_code(self.active_object_code)
                    w = obj_def.size.width if obj_def else 2
                    h = obj_def.size.height if obj_def else 2

                    if not self.current_screen.can_place_object(snap_x, snap_y, w, h, self.objects_lib.by_code):
                        self.status_message_requested.emit("Nie można umieścić obiektu: obszar jest zajęty przez inny obiekt lub wychodzi poza ekran.")
                        return

                    new_inst = ObjectInstance(code=self.active_object_code, x=snap_x, y=snap_y)
                    cmd = AddObjectCommand(self.current_screen, new_inst, on_change=self._on_model_changed)
                    self.undo_stack.push(cmd)
                    self.selected_instance = new_inst
                    self.selection_changed.emit(new_inst)
                    self.update()
                else:
                    self.status_message_requested.emit("Wybierz obiekt z listy po lewej stronie, aby go wstawić.")
            elif self.tool_mode == "MOVE":
                # Tryb 2: Przesuwanie obiektów
                self.selected_instance = hit
                self.selection_changed.emit(hit)
                if hit:
                    self.is_dragging = True
                    self.drag_start_x = snap_x
                    self.drag_start_y = snap_y
                    self.drag_orig_inst_x = hit.x
                    self.drag_orig_inst_y = hit.y
                    self._update_cursor()
                self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            if hit:
                # Usunięcie obiektu prawym przyciskiem
                cmd = RemoveObjectCommand(self.current_screen, hit, on_change=self._on_model_changed)
                self.undo_stack.push(cmd)
                if self.selected_instance == hit:
                    self.selected_instance = None
                    self.selection_changed.emit(None)
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self._update_cursor()
            if self.selected_instance and self.current_screen:
                final_x = self.selected_instance.x
                final_y = self.selected_instance.y
                sel_def = self.objects_lib.get_by_code(self.selected_instance.code)
                w_chars = sel_def.size.width if sel_def else 2
                h_chars = sel_def.size.height if sel_def else 2

                if final_x != self.drag_orig_inst_x or final_y != self.drag_orig_inst_y:
                    can_drop = self.current_screen.can_place_object(
                        final_x, final_y,
                        w_chars, h_chars,
                        self.objects_lib.by_code,
                        exclude=self.selected_instance
                    )
                    # Przywróć początkowe, aby model był spójny przed ew. MoveObjectCommand
                    self.selected_instance.x = self.drag_orig_inst_x
                    self.selected_instance.y = self.drag_orig_inst_y

                    if can_drop:
                        cmd = MoveObjectCommand(
                            self.current_screen,
                            self.selected_instance,
                            self.drag_orig_inst_x,
                            self.drag_orig_inst_y,
                            final_x,
                            final_y,
                            on_change=self._on_model_changed
                        )
                        self.undo_stack.push(cmd)
                    else:
                        self.status_message_requested.emit("Nie można przesunąć obiektu: docelowy obszar pokrywa się z innym obiektem!")
                        self._on_model_changed()
            self.update()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Backspace:
            self.delete_selected()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C:
            self.copy_selected()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V:
            self.paste_selected()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            self.undo_stack.undo()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and (key == Qt.Key.Key_Y or (modifiers & Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_Z)):
            self.undo_stack.redo()
        elif key == Qt.Key.Key_Escape:
            self.set_active_object(None)
            self.selected_instance = None
            self.selection_changed.emit(None)
            self.update()
        else:
            super().keyPressEvent(event)

    def delete_selected(self):
        if self.selected_instance and self.current_screen:
            cmd = RemoveObjectCommand(self.current_screen, self.selected_instance, on_change=self._on_model_changed)
            self.undo_stack.push(cmd)
            self.selected_instance = None
            self.selection_changed.emit(None)
            self.update()

    def copy_selected(self):
        if self.selected_instance:
            self.clipboard_instance = ObjectInstance(
                code=self.selected_instance.code,
                x=self.selected_instance.x,
                y=self.selected_instance.y
            )

    def paste_selected(self):
        if self.clipboard_instance and self.current_screen:
            clip_def = self.objects_lib.get_by_code(self.clipboard_instance.code)
            w = clip_def.size.width if clip_def else 2
            h = clip_def.size.height if clip_def else 2

            # Wklej w miejscu kursora hover lub z przesunięciem +2, +2
            target_x = self.hover_char_x if self.is_mouse_over else min(self.clipboard_instance.x + 2, SCREEN_WIDTH_CHARS - w)
            target_y = self.hover_char_y if self.is_mouse_over else min(self.clipboard_instance.y + 2, SCREEN_HEIGHT_CHARS - h)
            target_x = (target_x // GRID_STEP_X) * GRID_STEP_X
            target_y = (target_y // GRID_STEP_Y) * GRID_STEP_Y

            if not self.current_screen.can_place_object(target_x, target_y, w, h, self.objects_lib.by_code):
                self.status_message_requested.emit("Nie można wkleić obiektu: docelowy obszar jest zajęty lub wychodzi poza ekran!")
                return

            new_inst = ObjectInstance(code=self.clipboard_instance.code, x=target_x, y=target_y)
            cmd = AddObjectCommand(self.current_screen, new_inst, on_change=self._on_model_changed)
            self.undo_stack.push(cmd)
            self.selected_instance = new_inst
            self.selection_changed.emit(new_inst)
            self.update()

    def _on_model_changed(self):
        self.screen_modified.emit()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 1. Tło bazowe
        bg_rgb = self.renderer.palette.get_rgb(0)
        painter.fillRect(self.rect(), QColor(*bg_rgb))

        if not self.current_screen:
            # Komunikat o braku wybranego ekranu
            painter.setPen(QColor(180, 180, 180))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Brak wybranego ekranu. Utwórz lub wybierz ekran z biblioteki.")
            return

        # 2. Renderowanie obiektów ekranu
        for inst in self.current_screen.objects:
            obj_def = self.objects_lib.get_by_code(inst.code)
            if not obj_def:
                continue

            obj_pix = self.renderer.render_object_pixmap(obj_def, zoom=self.zoom)
            px = inst.x * CHAR_PIXEL_WIDTH * self.zoom
            py = inst.y * CHAR_PIXEL_HEIGHT * self.zoom
            painter.drawPixmap(px, py, obj_pix)

            # W trybie DESIGN rysuj granice i ID obiektu
            if self.mode == "DESIGN":
                rect = QRect(px, py, obj_pix.width(), obj_pix.height())
                painter.setPen(QPen(QColor(80, 130, 200, 120), 1))
                painter.drawRect(rect)

        # 3. Zaznaczenie wybranego obiektu (w trybie DESIGN)
        if self.mode == "DESIGN" and self.selected_instance:
            sel_def = self.objects_lib.get_by_code(self.selected_instance.code)
            w_chars = sel_def.size.width if sel_def else 2
            h_chars = sel_def.size.height if sel_def else 2
            
            sel_px = self.selected_instance.x * CHAR_PIXEL_WIDTH * self.zoom
            sel_py = self.selected_instance.y * CHAR_PIXEL_HEIGHT * self.zoom
            sel_w = w_chars * CHAR_PIXEL_WIDTH * self.zoom
            sel_h = h_chars * CHAR_PIXEL_HEIGHT * self.zoom
            
            sel_rect = QRect(sel_px, sel_py, sel_w, sel_h)
            pen_color = QColor(255, 230, 0)
            if self.is_dragging and self.current_screen:
                can_drop = self.current_screen.can_place_object(
                    self.selected_instance.x, self.selected_instance.y,
                    w_chars, h_chars,
                    self.objects_lib.by_code,
                    exclude=self.selected_instance
                )
                if not can_drop:
                    pen_color = QColor(255, 0, 0)

            painter.setPen(QPen(pen_color, 2, Qt.PenStyle.DashLine))
            painter.drawRect(sel_rect)

        # 4. Siatka 2x2 znaki (w trybie DESIGN)
        if self.mode == "DESIGN":
            cell_w = GRID_STEP_X * CHAR_PIXEL_WIDTH * self.zoom
            cell_h = GRID_STEP_Y * CHAR_PIXEL_HEIGHT * self.zoom

            painter.setPen(QPen(QColor(50, 60, 70, 80), 1, Qt.PenStyle.DotLine))
            # Linie pionowe
            for cx in range(0, SCREEN_WIDTH_PIXELS * self.zoom, cell_w):
                painter.drawLine(cx, 0, cx, self.height())
            # Linie poziome
            for cy in range(0, SCREEN_HEIGHT_PIXELS * self.zoom, cell_h):
                painter.drawLine(0, cy, self.width(), cy)

            # Zewnętrzna ramka ekranu
            painter.setPen(QPen(QColor(100, 120, 150), 2))
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        # 5. Podgląd "duszka" (ghost) przy najechaniu z wybranym obiektem do postawienia (tylko w trybie INSERT)
        if self.mode == "DESIGN" and self.tool_mode == "INSERT" and self.is_mouse_over and self.active_object_code is not None:
            ghost_def = self.objects_lib.get_by_code(self.active_object_code)
            if ghost_def:
                ghost_pix = self.renderer.render_object_pixmap(ghost_def, zoom=self.zoom)
                gx = self.hover_char_x * CHAR_PIXEL_WIDTH * self.zoom
                gy = self.hover_char_y * CHAR_PIXEL_HEIGHT * self.zoom
                
                painter.setOpacity(0.55)
                painter.drawPixmap(gx, gy, ghost_pix)
                painter.setOpacity(1.0)

                # Zarys na zielono / czerwono w zależności od granic i kolizji z innymi obiektami
                fits = self.current_screen.can_place_object(
                    self.hover_char_x, self.hover_char_y,
                    ghost_def.size.width, ghost_def.size.height,
                    self.objects_lib.by_code
                ) if self.current_screen else False
                border_color = QColor(0, 255, 0) if fits else QColor(255, 0, 0)
                painter.setPen(QPen(border_color, 2))
                painter.drawRect(gx, gy, ghost_pix.width(), ghost_pix.height())
