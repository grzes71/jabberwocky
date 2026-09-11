"""Główne okno aplikacji Labirynt Studio."""

from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QDockWidget, QToolBar, QStatusBar, QLabel, QComboBox, QFileDialog, 
    QMessageBox, QInputDialog
)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QUndoStack
from PySide6.QtCore import Qt

from ..model.models import Project, Screen, ObjectInstance, Labyrinth
from ..rendering.charset import Charset
from ..rendering.palette import AtariPalette
from ..rendering.renderer import AtariRenderer
from ..io.objects_loader import ObjectsLibrary
from ..io.project_io import load_project_from_yaml, save_project_to_yaml
from ..validation.validator import ProjectValidator
from .canvas_view import CanvasView
from .palette_widget import PaletteWidget
from .screens_widget import ScreensWidget
from .labyrinths_widget import LabyrinthsWidget
from .validation_widget import ValidationWidget
from .resource_dialog import ResourceDialog
from ..export.atari_export import export_labyrinth_binary


class MainWindow(QMainWindow):
    def __init__(
        self,
        objects_path: str = "world/objects.yaml",
        colors_path: str = "world/colors.yaml",
        charset_path: str = "fonts/game.fnt",
        project_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Labirynt Studio — Atari 8-bit Screen & Labyrinth Designer")
        self.resize(1360, 850)

        self.current_project_file: Optional[Path] = Path(project_path).resolve() if project_path else None
        self.is_dirty: bool = False

        # Inicjalizacja podsystemów
        self.objects_lib = ObjectsLibrary()
        self.palette = AtariPalette()
        self.charset = Charset()
        self.renderer = AtariRenderer(self.charset, self.palette)
        self.undo_stack = QUndoStack(self)
        self.validator = ProjectValidator(self.objects_lib)

        # Model projektu
        self.project = Project()

        # Wczytanie zasobów
        self.load_resources(objects_path, colors_path, charset_path)

        # Inicjalizacja GUI
        self._init_ui()

        # Otwórz projekt jeśli podany, lub utwórz domyślny ekran startowy
        if self.current_project_file and self.current_project_file.exists():
            self._load_project_file(self.current_project_file)
        else:
            self._create_default_project()

    def load_resources(self, obj_p: str, col_p: str, chr_p: str) -> bool:
        """Ładuje lub przeładowuje pliki zasobów."""
        ok_obj = self.objects_lib.load(obj_p)
        ok_col = self.palette.load(col_p)
        ok_chr = self.charset.load(chr_p)

        self.project.resources.objects = obj_p
        self.project.resources.colors = col_p
        self.project.resources.charset = chr_p

        return ok_obj and ok_col and ok_chr

    def _create_default_project(self):
        """Tworzy czysty projekt z jednym ekranem startowym FOREST_01."""
        self.project = Project(name="Jabberwocky")
        scr = Screen(id="FOREST_01", objects=[])
        self.project.add_screen(scr)
        self.screens_widget.set_project(self.project)
        self.labyrinths_widget.set_project(self.project)
        self._activate_screen("FOREST_01")
        self.undo_stack.clear()
        self._set_dirty(False)

    def _init_ui(self):
        # 1. Centralny Canvas w ScrollArea
        scroll_area = QScrollArea()
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setStyleSheet("background-color: #1e1e1e;")

        self.canvas = CanvasView(
            renderer=self.renderer,
            objects_lib=self.objects_lib,
            undo_stack=self.undo_stack,
            parent=self
        )
        self.canvas.screen_modified.connect(self._on_screen_modified)
        self.canvas.cursor_position_changed.connect(self._on_cursor_moved)
        self.canvas.selection_changed.connect(self._on_selection_changed)

        scroll_area.setWidget(self.canvas)
        self.setCentralWidget(scroll_area)

        # 2. Docki boczne
        self._init_docks()

        # 3. Paski menu i narzędzi
        self._init_actions()
        self._init_menus()
        self._init_toolbar()
        self._init_status_bar()

    def _init_docks(self):
        # Lewy dok: Paleta obiektów
        self.palette_dock = QDockWidget("Obiekty", self)
        self.palette_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.palette_widget = PaletteWidget(self.objects_lib, self.renderer, self)
        self.palette_widget.object_selected.connect(self._on_palette_object_selected)
        self.palette_dock.setWidget(self.palette_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.palette_dock)

        # Prawy dok górny: Biblioteka ekranów
        self.screens_dock = QDockWidget("Ekrany", self)
        self.screens_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.screens_widget = ScreensWidget(self.project, self)
        self.screens_widget.screen_activated.connect(self._activate_screen)
        self.screens_widget.screens_changed.connect(self._on_structure_changed)
        self.screens_dock.setWidget(self.screens_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.screens_dock)

        # Prawy dok dolny: Labirynty
        self.labyrinths_dock = QDockWidget("Labirynty", self)
        self.labyrinths_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.labyrinths_widget = LabyrinthsWidget(self.project, self)
        self.labyrinths_widget.screen_requested.connect(self._activate_screen)
        self.labyrinths_widget.labyrinths_changed.connect(self._on_structure_changed)
        self.labyrinths_dock.setWidget(self.labyrinths_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.labyrinths_dock)

        # Dolny dok: Walidacja
        self.validation_dock = QDockWidget("Walidacja projektu", self)
        self.validation_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        self.validation_widget = ValidationWidget(self)
        self.validation_widget.issue_activated.connect(self._on_issue_activated)
        self.validation_dock.setWidget(self.validation_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.validation_dock)

    def _init_actions(self):
        # Plik
        self.act_new = QAction("Nowy projekt", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self._action_new_project)

        self.act_open = QAction("Otwórz projekt...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._action_open_project)

        self.act_save = QAction("Zapisz projekt", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._action_save_project)

        self.act_save_as = QAction("Zapisz projekt jako...", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self._action_save_as_project)

        self.act_resources = QAction("Konfiguruj zasoby...", self)
        self.act_resources.triggered.connect(self._action_configure_resources)

        self.act_exit = QAction("Zakończ", self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.triggered.connect(self.close)

        # Edycja
        self.act_undo = self.undo_stack.createUndoAction(self, "Cofnij")
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)

        self.act_redo = self.undo_stack.createRedoAction(self, "Ponów")
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)

        self.act_copy = QAction("Kopiuj obiekt", self)
        self.act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.act_copy.triggered.connect(self.canvas.copy_selected)

        self.act_paste = QAction("Wklej obiekt", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.triggered.connect(self.canvas.paste_selected)

        self.act_delete = QAction("Usuń zaznaczony", self)
        self.act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.act_delete.triggered.connect(self.canvas.delete_selected)

        # Widok
        self.act_mode_design = QAction("Tryb DESIGN (Siatka)", self)
        self.act_mode_design.setCheckable(True)
        self.act_mode_design.setChecked(True)
        self.act_mode_design.triggered.connect(lambda: self._set_view_mode("DESIGN"))

        self.act_mode_atari = QAction("Tryb ATARI (Raster)", self)
        self.act_mode_atari.setCheckable(True)
        self.act_mode_atari.setChecked(False)
        self.act_mode_atari.triggered.connect(lambda: self._set_view_mode("ATARI"))

        # Narzędzia
        self.act_validate = QAction("Uruchom pełną walidację", self)
        self.act_validate.triggered.connect(self._run_validation)

        self.act_export_bin = QAction("Eksportuj labirynt do formatu binarnego Atari (.bin)...", self)
        self.act_export_bin.triggered.connect(self._action_export_binary)

    def _init_menus(self):
        menubar = self.menuBar()

        # Plik
        menu_file = menubar.addMenu("Plik")
        menu_file.addAction(self.act_new)
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)
        menu_file.addSeparator()
        menu_file.addAction(self.act_resources)
        menu_file.addSeparator()
        menu_file.addAction(self.act_exit)

        # Edycja
        menu_edit = menubar.addMenu("Edycja")
        menu_edit.addAction(self.act_undo)
        menu_edit.addAction(self.act_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_copy)
        menu_edit.addAction(self.act_paste)
        menu_edit.addAction(self.act_delete)

        # Widok
        menu_view = menubar.addMenu("Widok")
        menu_view.addAction(self.act_mode_design)
        menu_view.addAction(self.act_mode_atari)
        menu_view.addSeparator()
        menu_view.addAction(self.palette_dock.toggleViewAction())
        menu_view.addAction(self.screens_dock.toggleViewAction())
        menu_view.addAction(self.labyrinths_dock.toggleViewAction())
        menu_view.addAction(self.validation_dock.toggleViewAction())

        # Narzędzia
        menu_tools = menubar.addMenu("Narzędzia")
        menu_tools.addAction(self.act_validate)
        menu_tools.addAction(self.act_export_bin)

    def _init_toolbar(self):
        toolbar = QToolBar("Główny pasek narzędzi", self)
        self.addToolBar(toolbar)

        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()

        # Przełącznik trybu DESIGN / ATARI
        toolbar.addWidget(QLabel(" Tryb: "))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["DESIGN", "ATARI"])
        self.mode_combo.currentTextChanged.connect(self._set_view_mode)
        toolbar.addWidget(self.mode_combo)

        # Powiększenie Zoom
        toolbar.addWidget(QLabel("  Zoom: "))
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["2× (640×176)", "3× (960×264)", "4× (1280×352)", "6× (1920×528)"])
        self.zoom_combo.setCurrentIndex(2)  # Domyślnie 4x
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(self.zoom_combo)

        toolbar.addSeparator()
        toolbar.addAction(self.act_validate)

    def _init_status_bar(self):
        sb = self.statusBar()
        self.status_screen_label = QLabel("Ekran: -")
        self.status_objects_label = QLabel("Obiekty: 0")
        self.status_pos_label = QLabel("Kursor: (0, 0)")
        self.status_grid_label = QLabel("Siatka: 2×2 znaki")
        self.status_valid_label = QLabel("Status: OK")

        sb.addPermanentWidget(self.status_screen_label)
        sb.addPermanentWidget(self.status_objects_label)
        sb.addPermanentWidget(self.status_pos_label)
        sb.addPermanentWidget(self.status_grid_label)
        sb.addPermanentWidget(self.status_valid_label)

    def _set_dirty(self, dirty: bool):
        self.is_dirty = dirty
        title = "Labirynt Studio — Atari 8-bit Designer"
        if self.current_project_file:
            title += f" [{self.current_project_file.name}]"
        else:
            title += " [Nowy projekt]"
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)

    def _activate_screen(self, screen_id: str):
        screen = self.project.get_screen(screen_id)
        self.canvas.set_screen(screen)
        self.undo_stack.clear()
        self._update_status()
        self._run_validation()

    def _on_palette_object_selected(self, code: int):
        if code >= 0:
            self.canvas.set_active_object(code)
        else:
            self.canvas.set_active_object(None)

    def _on_screen_modified(self):
        self._set_dirty(True)
        self._update_status()
        self._run_validation()

    def _on_structure_changed(self):
        self._set_dirty(True)
        self._run_validation()

    def _on_cursor_moved(self, x: int, y: int):
        self.status_pos_label.setText(f"Kursor: ({x}, {y})")

    def _on_selection_changed(self, inst: Optional[ObjectInstance]):
        if inst:
            obj_def = self.objects_lib.get_by_code(inst.code)
            name = obj_def.id if obj_def else f"CODE_{inst.code}"
            self.statusBar().showMessage(f"Zaznaczono: {name} na pozycji ({inst.x}, {inst.y}), packed_xy={inst.packed_xy}")
        else:
            self.statusBar().showMessage("")

    def _update_status(self):
        if self.canvas.current_screen:
            self.status_screen_label.setText(f"Ekran: {self.canvas.current_screen.id}")
            self.status_objects_label.setText(f"Obiekty: {len(self.canvas.current_screen.objects)}")
        else:
            self.status_screen_label.setText("Ekran: -")
            self.status_objects_label.setText("Obiekty: 0")

    def _run_validation(self):
        issues = self.validator.validate_project(self.project)
        self.validation_widget.set_issues(issues)

        err_cnt = sum(1 for i in issues if i.severity == "ERROR")
        if err_cnt == 0:
            self.status_valid_label.setText("Status: Poprawny (OK)")
            self.status_valid_label.setStyleSheet("color: #4CAF50;")
        else:
            self.status_valid_label.setText(f"Status: {err_cnt} błędów!")
            self.status_valid_label.setStyleSheet("color: #F44336; font-weight: bold;")

    def _on_issue_activated(self, screen_id: str, x: int, y: int):
        self._activate_screen(screen_id)
        self.screens_widget.refresh(select_id=screen_id)

    def _set_view_mode(self, mode: str):
        self.canvas.set_mode(mode)
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(mode)
        self.mode_combo.blockSignals(False)

        self.act_mode_design.setChecked(mode == "DESIGN")
        self.act_mode_atari.setChecked(mode == "ATARI")

    def _on_zoom_changed(self, index: int):
        zooms = [2, 3, 4, 6]
        if 0 <= index < len(zooms):
            self.canvas.set_zoom(zooms[index])

    def _action_new_project(self):
        if self.is_dirty:
            resp = QMessageBox.question(
                self, "Niezapisane zmiany",
                "Projekt posiada niezapisane zmiany. Czy chcesz kontynuować?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

        self.current_project_file = None
        self._create_default_project()

    def _action_open_project(self):
        if self.is_dirty:
            resp = QMessageBox.question(
                self, "Niezapisane zmiany",
                "Projekt posiada niezapisane zmiany. Czy chcesz kontynuować?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

        file_path, _ = QFileDialog.getOpenFileName(self, "Otwórz projekt Labirynt Studio", "", "Projekt YAML (*.yaml *.yml)")
        if file_path:
            self._load_project_file(Path(file_path))

    def _load_project_file(self, path: Path):
        proj, err = load_project_from_yaml(path)
        if err or not proj:
            QMessageBox.critical(self, "Błąd wczytywania", f"Nie udało się wczytać projektu:\n{err}")
            return

        self.project = proj
        self.current_project_file = path

        # Wczytaj zasoby projektu jeśli ścieżki są określone
        base_dir = path.parent
        obj_p = (base_dir / proj.resources.objects).resolve()
        col_p = (base_dir / proj.resources.colors).resolve()
        chr_p = (base_dir / proj.resources.charset).resolve()

        self.load_resources(str(obj_p), str(col_p), str(chr_p))
        self.palette_widget.refresh()

        self.screens_widget.set_project(self.project)
        self.labyrinths_widget.set_project(self.project)

        if self.project.screens:
            self._activate_screen(self.project.screens[0].id)
            self.screens_widget.refresh(select_id=self.project.screens[0].id)
        else:
            self.canvas.set_screen(None)

        self._set_dirty(False)
        self._run_validation()

    def _action_save_project(self):
        if not self.current_project_file:
            self._action_save_as_project()
        else:
            success, err = save_project_to_yaml(self.project, self.current_project_file)
            if success:
                self._set_dirty(False)
                self.statusBar().showMessage(f"Zapisano projekt do {self.current_project_file.name}", 3000)
            else:
                QMessageBox.critical(self, "Błąd zapisu", f"Nie udało się zapisać projektu:\n{err}")

    def _action_save_as_project(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Zapisz projekt jako", "project.yaml", "Projekt YAML (*.yaml *.yml)")
        if file_path:
            path = Path(file_path)
            success, err = save_project_to_yaml(self.project, path)
            if success:
                self.current_project_file = path
                self._set_dirty(False)
                self.statusBar().showMessage(f"Zapisano projekt do {path.name}", 3000)
            else:
                QMessageBox.critical(self, "Błąd zapisu", f"Nie udało się zapisać projektu:\n{err}")

    def _action_configure_resources(self):
        dlg = ResourceDialog(
            objects_path=self.project.resources.objects,
            colors_path=self.project.resources.colors,
            charset_path=self.project.resources.charset,
            parent=self
        )
        if dlg.exec():
            obj_p, col_p, chr_p = dlg.get_paths()
            self.load_resources(obj_p, col_p, chr_p)
            self.palette_widget.refresh()
            self.canvas.update()
            self._set_dirty(True)
            self._run_validation()

    def _action_export_binary(self):
        if not self.project.labyrinths:
            QMessageBox.information(self, "Brak labiryntów", "Projekt nie zawiera żadnych zdefiniowanych labiryntów.")
            return

        lab_ids = [l.id for l in self.project.labyrinths]
        chosen_lab, ok = QInputDialog.getItem(self, "Eksport labiryntu", "Wybierz labirynt do eksportu:", lab_ids, 0, False)
        if not ok or not chosen_lab:
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Eksportuj binarny labirynt", f"{chosen_lab}.bin", "Plik binarny Atari (*.bin)")
        if out_path:
            success, err = export_labyrinth_binary(self.project, chosen_lab, out_path)
            if success:
                QMessageBox.information(self, "Sukces", f"Wyeksportowano labirynt {chosen_lab} do pliku:\n{out_path}")
            else:
                QMessageBox.critical(self, "Błąd eksportu", f"Nie udało się wyeksportować labiryntu:\n{err}")
