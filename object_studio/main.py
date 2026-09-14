import argparse
from pathlib import Path
import sys
import copy
from typing import Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                              QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
                              QCheckBox, QGroupBox, QMenuBar, QMenu, QFileDialog, QMessageBox, QPushButton, QColorDialog, QScrollArea, QListWidget, QListWidgetItem, QLabel, QSizePolicy)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt, QSettings

from object_studio.models import Project, ObjectDefinition, ObjectSize, ObjectFlags
from object_studio.charset import Charset
from object_studio.yaml_io import load_project, save_project, validate_project
from object_studio.settings import CANVAS_WIDTH_TILES, CANVAS_HEIGHT_TILES, DEFAULT_COLORS
from object_studio.widgets.palette_widget import PaletteWidget
from object_studio.widgets.canvas_widget import CanvasWidget
from object_studio.widgets.object_list_widget import ObjectListWidget
from object_studio.widgets.manage_tags_dialog import ManageTagsDialog
from object_studio.widgets.resource_dialog import ResourceDialog

class MainWindow(QMainWindow):
    def __init__(
        self,
        objects_path: str = "world/objects.yaml",
        colors_path: str = "world/colors.yaml",
        charset_path: str = "fonts/game.fnt",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Object Studio — Atari 8-bit Object Designer")
        self.project_path = None
        self.project = Project()
        self.charset = Charset()
        self.current_object = None

        self.objects_path = objects_path
        self.colors_path = colors_path
        self.charset_path = charset_path

        self._setup_ui()
        self._setup_menu()

        # Wczytanie zasobów
        self.load_resources(self.objects_path, self.colors_path, self.charset_path)

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Lewy panel: Lista obiektów
        left_panel = QGroupBox("Objects")
        left_layout = QVBoxLayout(left_panel)
        self.list_widget = ObjectListWidget()
        self.list_widget.object_selected.connect(self._on_object_selected)
        self.list_widget.add_requested.connect(self._on_add_object)
        self.list_widget.delete_requested.connect(self._on_delete_object)
        self.list_widget.copy_requested.connect(self._on_copy_object)
        self.list_widget.shift_requested.connect(self._on_shift_object)
        left_layout.addWidget(self.list_widget)
        main_layout.addWidget(left_panel, 1)

        # Środkowy panel: Paleta + Płótno
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        self.palette_widget = PaletteWidget()
        self.palette_widget.tile_selected.connect(self._on_brush_changed)
        center_layout.addWidget(self.palette_widget)

        self.canvas_widget = CanvasWidget()
        self.canvas_widget.canvas_changed.connect(self._on_canvas_changed)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.canvas_widget)
        
        center_layout.addWidget(scroll_area)
        
        main_layout.addWidget(center_panel, 3)

        # Prawy panel: Właściwości
        right_panel = QGroupBox("Properties")
        right_layout = QVBoxLayout(right_panel)
        
        form_layout = QFormLayout()

        self.edit_id = QLineEdit()
        self.edit_id.textChanged.connect(self._on_prop_changed)
        form_layout.addRow("ID:", self.edit_id)
        
        self.spin_code = QSpinBox()
        self.spin_code.setRange(0, 255)
        self.spin_code.valueChanged.connect(self._on_prop_changed)
        form_layout.addRow("Code:", self.spin_code)
        
        self.chk_blocking = QCheckBox()
        self.chk_blocking.stateChanged.connect(self._on_prop_changed)
        form_layout.addRow("Blocking:", self.chk_blocking)
        
        self.chk_interactive = QCheckBox()
        self.chk_interactive.stateChanged.connect(self._on_prop_changed)
        form_layout.addRow("Interactive:", self.chk_interactive)

        self.chk_secret = QCheckBox()
        self.chk_secret.stateChanged.connect(self._on_prop_changed)
        form_layout.addRow("Secret:", self.chk_secret)

        self.lbl_size = QLineEdit()
        self.lbl_size.setReadOnly(True)
        form_layout.addRow("Calculated Size:", self.lbl_size)
        
        right_layout.addLayout(form_layout)

        right_layout.addWidget(QLabel("Tags:"))
        self.tags_list_widget = QListWidget()
        self.tags_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tags_list_widget.itemChanged.connect(self._on_tags_item_changed)
        right_layout.addWidget(self.tags_list_widget, 1)
        
        main_layout.addWidget(right_panel, 1)
        self._enable_props(False)


    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        act_open_proj = QAction("Open objects.yaml...", self)
        act_open_proj.triggered.connect(self.action_open_project)
        file_menu.addAction(act_open_proj)
        
        act_save_proj = QAction("Save objects.yaml", self)
        act_save_proj.triggered.connect(self.action_save_project)
        file_menu.addAction(act_save_proj)
        
        file_menu.addSeparator()

        act_resources = QAction("Konfiguruj zasoby...", self)
        act_resources.triggered.connect(self.action_configure_resources)
        file_menu.addAction(act_resources)

        file_menu.addSeparator()
        
        act_load_char = QAction("Load game_font.fnt...", self)
        act_load_char.triggered.connect(self.action_load_charset)
        file_menu.addAction(act_load_char)

        tools_menu = menubar.addMenu("Tools")
        act_manage_tags = QAction("Zarządzaj tagami...", self)
        act_manage_tags.triggered.connect(self.action_manage_tags)
        tools_menu.addAction(act_manage_tags)
        
        color_menu = menubar.addMenu("Colors")
        
        act_bg = QAction("Background (COLBK)", self)
        act_bg.triggered.connect(lambda: self.action_change_color("BACKGROUND", 0))
        color_menu.addAction(act_bg)
        
        act_pf0 = QAction("Playfield 0 (COLPF0)", self)
        act_pf0.triggered.connect(lambda: self.action_change_color("PF0", 1))
        color_menu.addAction(act_pf0)
        
        act_pf1 = QAction("Playfield 1 (COLPF1)", self)
        act_pf1.triggered.connect(lambda: self.action_change_color("PF1", 2))
        color_menu.addAction(act_pf1)
        
        act_pf2 = QAction("Playfield 2 (COLPF2)", self)
        act_pf2.triggered.connect(lambda: self.action_change_color("PF2", 3))
        color_menu.addAction(act_pf2)
        
        act_pf3 = QAction("Playfield 3 / Inv (COLPF3)", self)
        act_pf3.triggered.connect(lambda: self.action_change_color("PF3_INV", 4))
        color_menu.addAction(act_pf3)
        
        color_menu.addSeparator()
        
        act_load_colors = QAction("Load Colors...", self)
        act_load_colors.triggered.connect(self.action_load_colors)
        color_menu.addAction(act_load_colors)
        
        act_save_colors = QAction("Save Colors...", self)
        act_save_colors.triggered.connect(self.action_save_colors)
        color_menu.addAction(act_save_colors)

    def _enable_props(self, enabled):
        self.edit_id.setEnabled(enabled)
        self.spin_code.setEnabled(enabled)
        self.chk_blocking.setEnabled(enabled)
        self.chk_interactive.setEnabled(enabled)
        self.chk_secret.setEnabled(enabled)
        self.tags_list_widget.setEnabled(enabled)
        if not enabled:
            self.tags_list_widget.blockSignals(True)
            self.tags_list_widget.clear()
            self.tags_list_widget.blockSignals(False)

    def load_resources(self, objects_path: str, colors_path: str, charset_path: str, save_settings: bool = False) -> bool:
        """Ładuje lub przeładowuje pliki zasobów (objects, colors, charset)."""
        self.objects_path = str(objects_path)
        self.colors_path = str(colors_path)
        self.charset_path = str(charset_path)

        ok_col = False
        p_col = Path(self.colors_path)
        if p_col.exists():
            ok_col = self._load_colors_from_file(p_col)
        else:
            self.list_widget.set_colors(DEFAULT_COLORS)

        ok_chr = False
        p_chr = Path(self.charset_path)
        if p_chr.exists():
            if self.charset.load(p_chr):
                self.palette_widget.set_charset(self.charset)
                self.canvas_widget.set_charset(self.charset)
                self.list_widget.set_charset(self.charset)
                ok_chr = True

        ok_obj = False
        p_obj = Path(self.objects_path)
        if p_obj.exists():
            self.project_path = p_obj
            self.project = load_project(self.project_path)
            self.list_widget.set_project(self.project)
            self._on_tags_updated()
            ok_obj = True

        if save_settings:
            # Zapisz w QSettings
            settings = QSettings("Atari", "ObjectStudio")
            settings.setValue("objects_path", self.objects_path)
            settings.setValue("colors_path", self.colors_path)
            settings.setValue("charset_path", self.charset_path)

        return ok_obj and ok_col and ok_chr

    def _load_colors_from_file(self, path: Path) -> bool:
        import yaml
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    if "colors" in data:
                        data = data["colors"]
                    for k, v in data.items():
                        if k in DEFAULT_COLORS:
                            if isinstance(v, dict) and "rgb" in v:
                                DEFAULT_COLORS[k] = tuple(v["rgb"])
                            elif isinstance(v, list) and len(v) == 3:
                                DEFAULT_COLORS[k] = tuple(v)
                    self.palette_widget.set_colors(DEFAULT_COLORS)
                    self.canvas_widget.set_colors(DEFAULT_COLORS)
                    self.list_widget.set_colors(DEFAULT_COLORS)
            return True
        except Exception:
            return False

    def action_configure_resources(self):
        dlg = ResourceDialog(
            objects_path=self.objects_path,
            colors_path=self.colors_path,
            charset_path=self.charset_path,
            parent=self
        )
        if dlg.exec():
            obj_p, col_p, chr_p = dlg.get_paths()
            self.load_resources(obj_p, col_p, chr_p, save_settings=True)
            self.statusBar().showMessage("Zasoby zostały pomyślnie zaktualizowane.", 3000)

    def action_load_charset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Charset", "", "Atari Font (*.fnt);;All Files (*)")
        if path:
            if self.charset.load(Path(path)):
                self.charset_path = str(path)
                QSettings("Atari", "ObjectStudio").setValue("charset_path", self.charset_path)
                self.palette_widget.set_charset(self.charset)
                self.canvas_widget.set_charset(self.charset)
                self.list_widget.set_charset(self.charset)
            else:
                QMessageBox.warning(self, "Error", "Failed to load charset (must be 1024 bytes).")

    def action_change_color(self, name, index):
        current_rgb = DEFAULT_COLORS[name]
        current_color = QColor(*current_rgb)
        
        new_color = QColorDialog.getColor(current_color, self, f"Select color for {name}")
        if new_color.isValid():
            DEFAULT_COLORS[name] = (new_color.red(), new_color.green(), new_color.blue())
            self.palette_widget.set_colors(DEFAULT_COLORS)
            self.canvas_widget.set_colors(DEFAULT_COLORS)
            self.list_widget.set_colors(DEFAULT_COLORS)

    def action_load_colors(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Colors", "", "YAML (*.yaml);;All Files (*)")
        if path:
            if self._load_colors_from_file(Path(path)):
                self.colors_path = str(path)
                QSettings("Atari", "ObjectStudio").setValue("colors_path", self.colors_path)
            else:
                QMessageBox.warning(self, "Error", f"Failed to load colors from {path}")

    def action_save_colors(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Colors", "region.yaml", "YAML (*.yaml);;All Files (*)")
        if path:
            import yaml
            try:
                c_data = {k: {"rgb": list(v), "atari": 0} for k, v in DEFAULT_COLORS.items()}
                if Path(path).exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        file_data = yaml.safe_load(f) or {}
                    if "id" in file_data or "name" in file_data:
                        file_data["colors"] = c_data
                    else:
                        file_data = c_data
                else:
                    file_data = c_data
                    
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(file_data, f, default_flow_style=False, sort_keys=False)
                QMessageBox.information(self, "Saved", "Colors saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save colors:\n{e}")

    def action_open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "YAML (*.yaml);;All Files (*)")
        if path:
            self.objects_path = str(path)
            self.project_path = Path(path)
            QSettings("Atari", "ObjectStudio").setValue("objects_path", self.objects_path)
            self.project = load_project(self.project_path)
            self.list_widget.set_project(self.project)
            self.current_object = None
            self.canvas_widget.clear()
            self._enable_props(False)
            self._on_tags_updated()

    def action_manage_tags(self):
        if not self.project:
            QMessageBox.warning(self, "Brak projektu", "Najpierw otwórz plik z obiektami (objects.yaml).")
            return
        dialog = ManageTagsDialog(self.project, self)
        dialog.tags_changed.connect(self._on_tags_updated)
        dialog.exec()
        self._on_tags_updated()

    def _refresh_tags_properties(self):
        self.tags_list_widget.blockSignals(True)
        self.tags_list_widget.clear()
        if self.current_object and self.project:
            for tag in self.project.available_tags:
                item = QListWidgetItem(tag)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if tag in self.current_object.tags:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.tags_list_widget.addItem(item)
        self.tags_list_widget.blockSignals(False)

    def _on_tags_item_changed(self, item):
        if not self.current_object:
            return
        selected_tags = []
        for i in range(self.tags_list_widget.count()):
            it = self.tags_list_widget.item(i)
            if it.checkState() == Qt.Checked:
                selected_tags.append(it.text())
        self.current_object.tags = selected_tags
        self.list_widget.refresh_list(select_obj=self.current_object)

    def _on_tags_updated(self):
        self.list_widget.update_tag_filter_options()
        self._refresh_tags_properties()
        self.list_widget.refresh_list(select_obj=self.current_object)

    def action_save_project(self):
        if not self.project_path:
            QMessageBox.warning(self, "Error", "No project loaded.")
            return
            
        errors = validate_project(self.project)
        if errors:
            msg = "\n".join(errors)
            QMessageBox.critical(self, "Validation Errors", f"Cannot save due to validation errors:\n{msg}")
            return
            
        if save_project(self.project_path, self.project):
            QMessageBox.information(self, "Saved", "objects.yaml saved successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save objects.yaml.")

    def _on_brush_changed(self, index):
        self.canvas_widget.set_brush(index)

    def _on_object_selected(self, obj: ObjectDefinition):
        self.current_object = obj
        if not obj:
            self._enable_props(False)
            self.canvas_widget.clear()
            return
            
        self._enable_props(True)
        # Block signals to avoid loop
        self.edit_id.blockSignals(True)
        self.spin_code.blockSignals(True)
        self.chk_blocking.blockSignals(True)
        self.chk_interactive.blockSignals(True)
        self.chk_secret.blockSignals(True)
        
        self.edit_id.setText(obj.id)
        self.spin_code.setValue(obj.code)
        self.chk_blocking.setChecked(obj.flags.blocking)
        self.chk_interactive.setChecked(obj.flags.interactive)
        self.chk_secret.setChecked(obj.flags.secret)
        self.lbl_size.setText(f"{obj.size.width} x {obj.size.height}")
        
        self.edit_id.blockSignals(False)
        self.spin_code.blockSignals(False)
        self.chk_blocking.blockSignals(False)
        self.chk_interactive.blockSignals(False)
        self.chk_secret.blockSignals(False)

        self._refresh_tags_properties()

        # Load tiles into canvas (block signal)
        self.canvas_widget.blockSignals(True)
        self.canvas_widget.set_grid(obj.tiles, obj.size.width, obj.size.height)
        self.canvas_widget.blockSignals(False)

    def _on_add_object(self):
        new_code = max([o.code for o in self.project.objects], default=0) + 1
        new_obj = ObjectDefinition(id=f"NEW_OBJECT_{new_code}", code=new_code)
        self.project.objects.append(new_obj)
        self.list_widget.refresh_list(select_obj=new_obj)

    def _on_delete_object(self, obj: ObjectDefinition):
        if obj in self.project.objects:
            self.project.objects.remove(obj)
            self.current_object = None
            self.list_widget.refresh_list()

    def _on_copy_object(self, obj: ObjectDefinition):
        new_code = max([o.code for o in self.project.objects], default=0) + 1
        new_obj = copy.deepcopy(obj)
        new_obj.id = f"{obj.id}_COPY"
        new_obj.code = new_code
        self.project.objects.append(new_obj)
        self.list_widget.refresh_list(select_obj=new_obj)

    def _on_shift_object(self, obj: ObjectDefinition, direction: str):
        if not obj: return
        
        if self.current_object != obj:
            self._on_object_selected(obj)
            
        grid = self.canvas_widget.get_grid()
        from object_studio.settings import CANVAS_WIDTH_TILES, CANVAS_HEIGHT_TILES
        cols = CANVAS_WIDTH_TILES
        rows = CANVAS_HEIGHT_TILES
        
        min_x = cols
        max_x = -1
        min_y = rows
        max_y = -1
        
        for y in range(rows):
            for x in range(cols):
                if grid[y][x] != 0:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
                    
        if max_x == -1: return 
        
        if direction == 'right' and max_x >= cols - 1: return
        if direction == 'left' and min_x <= 0: return
        if direction == 'down' and max_y >= rows - 1: return
        if direction == 'up' and min_y <= 0: return
        
        new_grid = [[0 for _ in range(cols)] for _ in range(rows)]
        dx = 0
        dy = 0
        if direction == 'right': dx = 1
        elif direction == 'left': dx = -1
        elif direction == 'down': dy = 1
        elif direction == 'up': dy = -1
        
        for y in range(rows):
            for x in range(cols):
                if grid[y][x] != 0:
                    new_grid[y+dy][x+dx] = grid[y][x]
                    
        self.canvas_widget.grid = new_grid
        self.canvas_widget.update()
        
        self._on_canvas_changed()

    def _on_prop_changed(self):
        if not self.current_object:
            return
        self.current_object.id = self.edit_id.text()
        self.current_object.code = self.spin_code.value()
        self.current_object.flags.blocking = self.chk_blocking.isChecked()
        self.current_object.flags.interactive = self.chk_interactive.isChecked()
        self.current_object.flags.secret = self.chk_secret.isChecked()
        
        self.list_widget.update_object_item(self.current_object)

    def _on_canvas_changed(self):
        if not self.current_object:
            return
            
        grid = self.canvas_widget.get_grid()
        
        max_x = -1
        max_y = -1
        
        for y in range(CANVAS_HEIGHT_TILES):
            for x in range(CANVAS_WIDTH_TILES):
                if grid[y][x] != 0:
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
                    
        if max_x == -1: # Empty canvas
            self.current_object.size.width = 1
            self.current_object.size.height = 1
            self.current_object.tiles = [0]
            self.lbl_size.setText("1 x 1")
            self.list_widget.update_object_item(self.current_object)
            return
            
        # Do not trim spaces on the left and top (min_x and min_y are always 0)
        min_x = 0
        min_y = 0
        w = max_x + 1
        h = max_y + 1
        self.current_object.size.width = w
        self.current_object.size.height = h
        self.lbl_size.setText(f"{w} x {h}")
        
        # Extract tiles
        tiles = []
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                tiles.append(grid[y][x])
                
        self.current_object.tiles = tiles
        self.list_widget.update_object_item(self.current_object)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 
            'Quit Object Studio', 
            "Czy na pewno chcesz wyjść z aplikacji? (Are you sure you want to quit? You might have unsaved changes.)",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def parse_args():
    parser = argparse.ArgumentParser(
        description="Object Studio — Narzędzie GUI do edycji obiektów dla Atari 8-bit."
    )
    parser.add_argument(
        "--objects",
        type=str,
        default="world/objects.yaml",
        help="Ścieżka do pliku objects.yaml (domyślnie: world/objects.yaml)"
    )
    parser.add_argument(
        "--colors",
        type=str,
        default="world/colors.yaml",
        help="Ścieżka do pliku colors.yaml (domyślnie: world/colors.yaml)"
    )
    parser.add_argument(
        "--charset",
        type=str,
        default="fonts/game.fnt",
        help="Ścieżka do pliku charsetu Atari .fnt (domyślnie: fonts/game.fnt)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = app.font()
    font.setPointSize(9)
    app.setFont(font)

    settings = QSettings("Atari", "ObjectStudio")
    stored_obj = settings.value("objects_path", args.objects, type=str)
    stored_col = settings.value("colors_path", args.colors, type=str)
    stored_chr = settings.value("charset_path", args.charset, type=str)

    obj_path = args.objects if "--objects" in sys.argv else stored_obj
    col_path = args.colors if "--colors" in sys.argv else stored_col
    chr_path = args.charset if "--charset" in sys.argv else stored_chr

    # Weryfikacja dostępności plików zasobów
    missing = []
    if not Path(obj_path).exists():
        missing.append(f"Obiekty: {obj_path}")
    if not Path(col_path).exists():
        missing.append(f"Kolory: {col_path}")
    if not Path(chr_path).exists():
        missing.append(f"Charset: {chr_path}")

    # Jeśli brakuje zasobów, nie rzucaj tracebackiem — pozwól wskazać pliki w oknie dialogowym
    if missing:
        QMessageBox.information(
            None,
            "Konfiguracja zasobów",
            "Niektóre pliki zasobów nie zostały odnalezione:\n" +
            "\n".join(missing) +
            "\n\nWskaż poprawne ścieżki w kolejnym oknie."
        )
        dialog = ResourceDialog(
            objects_path=obj_path,
            colors_path=col_path,
            charset_path=chr_path
        )
        if dialog.exec():
            obj_path, col_path, chr_path = dialog.get_paths()
            settings.setValue("objects_path", obj_path)
            settings.setValue("colors_path", col_path)
            settings.setValue("charset_path", chr_path)
        else:
            sys.exit(0)

    window = MainWindow(
        objects_path=obj_path,
        colors_path=col_path,
        charset_path=chr_path
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
