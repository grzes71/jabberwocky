"""Panel boczny zarządzania labiryntami i przypisywaniem do nich ekranów."""

from typing import Optional, Set, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QInputDialog, QMessageBox, QLabel, QSplitter,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from ..model.models import Project, Labyrinth


class LabyrinthDialog(QDialog):
    """Okno dialogowe tworzenia oraz edycji ID i nazwy poziomu labiryntu."""

    def __init__(
        self,
        lab_id: str = "",
        lab_name: str = "",
        existing_ids: Optional[Set[str]] = None,
        is_new: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Nowy labirynt" if is_new else f"Edycja poziomu — {lab_id}")
        self.setMinimumWidth(360)

        layout = QFormLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.id_edit = QLineEdit(lab_id)
        self.id_edit.setPlaceholderText("np. LEVEL_01")
        self.name_edit = QLineEdit(lab_name)
        self.name_edit.setPlaceholderText("np. Tulgey Forest")

        layout.addRow("ID labiryntu:", self.id_edit)
        layout.addRow("Nazwa poziomu:", self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.existing_ids = existing_ids or set()
        self.old_id = lab_id if not is_new else None
        self.is_new = is_new

        if is_new:
            self.id_edit.setFocus()
        else:
            self.name_edit.setFocus()
            self.name_edit.selectAll()

    def _validate_and_accept(self):
        clean_id = self.id_edit.text().strip().upper()
        if not clean_id:
            QMessageBox.warning(self, "Błąd", "ID labiryntu nie może być puste.")
            self.id_edit.setFocus()
            return
        if self.is_new or clean_id != self.old_id:
            if clean_id in self.existing_ids:
                QMessageBox.warning(self, "Błąd", f"Labirynt o ID '{clean_id}' już istnieje.")
                self.id_edit.setFocus()
                return
        self.accept()

    def get_data(self) -> Tuple[str, str]:
        return self.id_edit.text().strip().upper(), self.name_edit.text().strip()


class LabyrinthsWidget(QWidget):
    screen_requested = Signal(str)  # Emituje ID ekranu do załadowania na płótnie
    labyrinths_changed = Signal()

    def __init__(self, project: Project, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. Górna sekcja: Lista labiryntów
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(QLabel("<b>Labirynty:</b>"))

        self.lab_list = QListWidget()
        self.lab_list.currentItemChanged.connect(self._on_lab_selected)
        self.lab_list.itemDoubleClicked.connect(self._on_lab_double_clicked)
        top_layout.addWidget(self.lab_list)

        lab_btns_1 = QHBoxLayout()
        self.btn_new_lab = QPushButton("Nowy")
        self.btn_new_lab.clicked.connect(self._create_labyrinth)
        self.btn_rename_lab = QPushButton("Zmień nazwę")
        self.btn_rename_lab.clicked.connect(self._rename_labyrinth)
        lab_btns_1.addWidget(self.btn_new_lab)
        lab_btns_1.addWidget(self.btn_rename_lab)
        top_layout.addLayout(lab_btns_1)

        lab_btns_2 = QHBoxLayout()
        self.btn_delete_lab = QPushButton("Usuń")
        self.btn_delete_lab.clicked.connect(self._delete_labyrinth)
        lab_btns_2.addWidget(self.btn_delete_lab)
        top_layout.addLayout(lab_btns_2)

        splitter.addWidget(top_widget)

        # 2. Dolna sekcja: Ekrany w wybranym labiryncie
        bot_widget = QWidget()
        bot_layout = QVBoxLayout(bot_widget)
        bot_layout.setContentsMargins(0, 0, 0, 0)
        bot_layout.addWidget(QLabel("<b>Ekrany w labiryncie:</b>"))

        self.screen_list = QListWidget()
        self.screen_list.itemDoubleClicked.connect(self._on_screen_double_clicked)
        bot_layout.addWidget(self.screen_list)

        screen_btns = QHBoxLayout()
        self.btn_add_screen = QPushButton("+ Ekran")
        self.btn_add_screen.clicked.connect(self._add_screen_to_lab)
        self.btn_rem_screen = QPushButton("- Ekran")
        self.btn_rem_screen.clicked.connect(self._remove_screen_from_lab)
        self.btn_up = QPushButton("▲")
        self.btn_up.clicked.connect(self._move_screen_up)
        self.btn_down = QPushButton("▼")
        self.btn_down.clicked.connect(self._move_screen_down)

        screen_btns.addWidget(self.btn_add_screen)
        screen_btns.addWidget(self.btn_rem_screen)
        screen_btns.addWidget(self.btn_up)
        screen_btns.addWidget(self.btn_down)
        bot_layout.addLayout(screen_btns)

        splitter.addWidget(bot_widget)
        layout.addWidget(splitter)

        self.refresh()

    def set_project(self, project: Project):
        self.project = project
        self.refresh()

    def refresh(self, select_id: Optional[str] = None):
        cur_lab_id = select_id
        if not cur_lab_id and self.lab_list.currentItem():
            cur_lab_id = self.lab_list.currentItem().data(Qt.ItemDataRole.UserRole)

        self.lab_list.blockSignals(True)
        self.lab_list.clear()

        selected_item = None
        for lab in self.project.labyrinths:
            label = f"{lab.id} ({lab.name})" if lab.name else lab.id
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, lab.id)
            self.lab_list.addItem(item)
            if cur_lab_id and lab.id == cur_lab_id:
                selected_item = item

        self.lab_list.blockSignals(False)

        if selected_item:
            self.lab_list.setCurrentItem(selected_item)
        elif self.lab_list.count() > 0:
            self.lab_list.setCurrentRow(0)
        else:
            self.screen_list.clear()

    def _get_current_lab(self) -> Optional[Labyrinth]:
        cur = self.lab_list.currentItem()
        if not cur:
            return None
        lab_id = cur.data(Qt.ItemDataRole.UserRole)
        return self.project.get_labyrinth(lab_id)

    def _on_lab_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        self.screen_list.clear()
        if not current:
            return
        lab = self._get_current_lab()
        if not lab:
            return

        for sid in lab.screens:
            item = QListWidgetItem(sid)
            item.setData(Qt.ItemDataRole.UserRole, sid)
            self.screen_list.addItem(item)

    def _on_lab_double_clicked(self, item: QListWidgetItem):
        self._rename_labyrinth()

    def _on_screen_double_clicked(self, item: QListWidgetItem):
        sid = item.data(Qt.ItemDataRole.UserRole)
        if sid:
            self.screen_requested.emit(sid)

    def _create_labyrinth(self):
        existing_ids = {l.id for l in self.project.labyrinths}
        dlg = LabyrinthDialog(existing_ids=existing_ids, is_new=True, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            clean_id, name = dlg.get_data()
            new_lab = Labyrinth(id=clean_id, name=name, screens=[])
            self.project.labyrinths.append(new_lab)
            self.refresh(select_id=clean_id)
            self.labyrinths_changed.emit()

    def _rename_labyrinth(self):
        lab = self._get_current_lab()
        if not lab:
            QMessageBox.information(self, "Informacja", "Najpierw wybierz labirynt z listy.")
            return
        existing_ids = {l.id for l in self.project.labyrinths}
        dlg = LabyrinthDialog(
            lab_id=lab.id,
            lab_name=lab.name,
            existing_ids=existing_ids,
            is_new=False,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            clean_id, name = dlg.get_data()
            if clean_id != lab.id or name != lab.name:
                lab.id = clean_id
                lab.name = name
                self.refresh(select_id=clean_id)
                self.labyrinths_changed.emit()

    def _delete_labyrinth(self):
        lab = self._get_current_lab()
        if not lab:
            return
        resp = QMessageBox.question(
            self, "Usuń labirynt",
            f"Czy na pewno usunąć labirynt '{lab.id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.project.labyrinths.remove(lab)
            self.refresh()
            self.labyrinths_changed.emit()

    def _add_screen_to_lab(self):
        lab = self._get_current_lab()
        if not lab:
            QMessageBox.information(self, "Informacja", "Najpierw wybierz lub utwórz labirynt.")
            return

        all_screen_ids = [s.id for s in self.project.screens]
        if not all_screen_ids:
            QMessageBox.information(self, "Informacja", "Brak dostępnych ekranów w projekcie.")
            return

        chosen_id, ok = QInputDialog.getItem(
            self, "Dodaj ekran do labiryntu",
            "Wybierz ekran:", all_screen_ids, 0, False
        )
        if ok and chosen_id:
            lab.screens.append(chosen_id)
            self._on_lab_selected(self.lab_list.currentItem(), None)
            self.labyrinths_changed.emit()

    def _remove_screen_from_lab(self):
        lab = self._get_current_lab()
        cur_row = self.screen_list.currentRow()
        if lab and 0 <= cur_row < len(lab.screens):
            lab.screens.pop(cur_row)
            self._on_lab_selected(self.lab_list.currentItem(), None)
            self.labyrinths_changed.emit()

    def _move_screen_up(self):
        lab = self._get_current_lab()
        row = self.screen_list.currentRow()
        if lab and row > 0:
            lab.screens[row - 1], lab.screens[row] = lab.screens[row], lab.screens[row - 1]
            self._on_lab_selected(self.lab_list.currentItem(), None)
            self.screen_list.setCurrentRow(row - 1)
            self.labyrinths_changed.emit()

    def _move_screen_down(self):
        lab = self._get_current_lab()
        row = self.screen_list.currentRow()
        if lab and 0 <= row < len(lab.screens) - 1:
            lab.screens[row], lab.screens[row + 1] = lab.screens[row + 1], lab.screens[row]
            self._on_lab_selected(self.lab_list.currentItem(), None)
            self.screen_list.setCurrentRow(row + 1)
            self.labyrinths_changed.emit()
