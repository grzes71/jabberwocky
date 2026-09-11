"""Panel boczny zarządzania biblioteką ekranów (tworzenie, duplikowanie, zmiana nazwy, usuwanie)."""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from ..model.models import Project, Screen


class ScreensWidget(QWidget):
    screen_activated = Signal(str)  # Emituje ID wybranego ekranu
    screens_changed = Signal()      # Emituje gdy dodano/usunięto/zmieniono ekran

    def __init__(self, project: Project, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Lista ekranów
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_current_changed)
        layout.addWidget(self.list_widget)

        # Przyciski akcji
        btn_layout_1 = QHBoxLayout()
        self.btn_new = QPushButton("Nowy")
        self.btn_new.clicked.connect(self._create_screen)
        self.btn_duplicate = QPushButton("Duplikuj")
        self.btn_duplicate.clicked.connect(self._duplicate_screen)
        btn_layout_1.addWidget(self.btn_new)
        btn_layout_1.addWidget(self.btn_duplicate)
        layout.addLayout(btn_layout_1)

        btn_layout_2 = QHBoxLayout()
        self.btn_rename = QPushButton("Zmień nazwę")
        self.btn_rename.clicked.connect(self._rename_screen)
        self.btn_delete = QPushButton("Usuń")
        self.btn_delete.clicked.connect(self._delete_screen)
        btn_layout_2.addWidget(self.btn_rename)
        btn_layout_2.addWidget(self.btn_delete)
        layout.addLayout(btn_layout_2)

        self.refresh()

    def set_project(self, project: Project):
        self.project = project
        self.refresh()

    def refresh(self, select_id: Optional[str] = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        selected_item = None
        for screen in self.project.screens:
            obj_count = len(screen.objects)
            item = QListWidgetItem(f"{screen.id} ({obj_count} ob.)")
            item.setData(Qt.ItemDataRole.UserRole, screen.id)
            self.list_widget.addItem(item)
            if select_id and screen.id == select_id:
                selected_item = item

        self.list_widget.blockSignals(False)

        if selected_item:
            self.list_widget.setCurrentItem(selected_item)
        elif self.list_widget.count() > 0 and not self.list_widget.currentItem():
            self.list_widget.setCurrentRow(0)

    def _on_current_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            screen_id = current.data(Qt.ItemDataRole.UserRole)
            self.screen_activated.emit(screen_id)

    def _create_screen(self):
        screen_id, ok = QInputDialog.getText(self, "Nowy ekran", "Podaj unikalne ID ekranu (np. FOREST_01):")
        if ok and screen_id.strip():
            clean_id = screen_id.strip().upper()
            if self.project.get_screen(clean_id):
                QMessageBox.warning(self, "Błąd", f"Ekran o ID '{clean_id}' już istnieje.")
                return
            new_screen = Screen(id=clean_id, objects=[])
            self.project.add_screen(new_screen)
            self.refresh(select_id=clean_id)
            self.screens_changed.emit()
            self.screen_activated.emit(clean_id)

    def _duplicate_screen(self):
        cur_item = self.list_widget.currentItem()
        if not cur_item:
            return
        src_id = cur_item.data(Qt.ItemDataRole.UserRole)
        new_id, ok = QInputDialog.getText(self, "Duplikuj ekran", "Podaj ID dla kopii ekranu:", text=f"{src_id}_COPY")
        if ok and new_id.strip():
            clean_id = new_id.strip().upper()
            if self.project.get_screen(clean_id):
                QMessageBox.warning(self, "Błąd", f"Ekran o ID '{clean_id}' już istnieje.")
                return
            dup = self.project.duplicate_screen(src_id, clean_id)
            if dup:
                self.refresh(select_id=clean_id)
                self.screens_changed.emit()
                self.screen_activated.emit(clean_id)

    def _rename_screen(self):
        cur_item = self.list_widget.currentItem()
        if not cur_item:
            return
        old_id = cur_item.data(Qt.ItemDataRole.UserRole)
        new_id, ok = QInputDialog.getText(self, "Zmień nazwę ekranu", "Podaj nowe ID ekranu:", text=old_id)
        if ok and new_id.strip() and new_id.strip().upper() != old_id:
            clean_id = new_id.strip().upper()
            if self.project.get_screen(clean_id):
                QMessageBox.warning(self, "Błąd", f"Ekran o ID '{clean_id}' już istnieje.")
                return
            screen = self.project.get_screen(old_id)
            if screen:
                screen.id = clean_id
                # Aktualizuj też odwołania w labiryntach
                for lab in self.project.labyrinths:
                    lab.screens = [clean_id if sid == old_id else sid for sid in lab.screens]
                self.refresh(select_id=clean_id)
                self.screens_changed.emit()
                self.screen_activated.emit(clean_id)

    def _delete_screen(self):
        cur_item = self.list_widget.currentItem()
        if not cur_item:
            return
        screen_id = cur_item.data(Qt.ItemDataRole.UserRole)
        resp = QMessageBox.question(
            self, "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć ekran '{screen_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.project.remove_screen(screen_id)
            self.refresh()
            self.screens_changed.emit()
            new_cur = self.list_widget.currentItem()
            if new_cur:
                self.screen_activated.emit(new_cur.data(Qt.ItemDataRole.UserRole))
            else:
                self.screen_activated.emit("")
