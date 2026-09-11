"""Panel boczny z listą obiektów, wyszukiwarką, filtrem tagów oraz podglądem właściwości."""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, 
    QListWidget, QListWidgetItem, QLabel, QGroupBox, QScrollArea, QSplitter
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, Signal, QSize

from ..io.objects_loader import ObjectsLibrary
from ..rendering.renderer import AtariRenderer
from ..model.models import ObjectDefinition


class PaletteWidget(QWidget):
    object_selected = Signal(int)  # Emituje code obiektu lub -1 gdy odznaczono

    def __init__(self, objects_lib: ObjectsLibrary, renderer: AtariRenderer, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.objects_lib = objects_lib
        self.renderer = renderer

        self.selected_code: Optional[int] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Wyszukiwarka
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Szukaj obiektu...")
        self.search_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_input)

        # Filtr tagów
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("WSZYSTKIE TAGI")
        for tag in sorted(self.objects_lib.tags):
            self.tag_combo.addItem(tag)
        self.tag_combo.currentTextChanged.connect(self._apply_filter)
        layout.addWidget(self.tag_combo)

        # Splitter na listę i panel szczegółów
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Lista obiektów
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        splitter.addWidget(self.list_widget)

        # Panel szczegółów wybranego obiektu
        self.details_group = QGroupBox("Właściwości obiektu")
        details_layout = QVBoxLayout(self.details_group)
        details_layout.setContentsMargins(6, 6, 6, 6)

        # Podgląd graficzny duży
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #111; border: 1px solid #444; border-radius: 4px; padding: 4px;")
        self.preview_label.setFixedHeight(80)
        details_layout.addWidget(self.preview_label)

        # Tekstowe właściwości
        self.info_label = QLabel("Wybierz obiekt z listy")
        self.info_label.setWordWrap(True)
        details_layout.addWidget(self.info_label)

        splitter.addWidget(self.details_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self._populate_list()

    def refresh(self):
        """Odświeża listę i tagi po przeładowaniu zasobów."""
        cur_tag = self.tag_combo.currentText()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("WSZYSTKIE TAGI")
        for tag in sorted(self.objects_lib.tags):
            self.tag_combo.addItem(tag)
        idx = self.tag_combo.findText(cur_tag)
        if idx >= 0:
            self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)

        self._populate_list()

    def _populate_list(self):
        self.list_widget.clear()
        search_query = self.search_input.text().strip().lower()
        selected_tag = self.tag_combo.currentText()

        for obj in self.objects_lib.objects:
            if selected_tag != "WSZYSTKIE TAGI" and selected_tag not in obj.tags:
                continue
            if search_query:
                match_id = search_query in obj.id.lower()
                match_code = search_query == str(obj.code)
                match_tag = any(search_query in t.lower() for t in obj.tags)
                if not (match_id or match_code or match_tag):
                    continue

            # Generuj ikonę
            pix = self.renderer.render_object_pixmap(obj, zoom=2)
            icon = QIcon(pix)

            item = QListWidgetItem(icon, f"{obj.id} (#{obj.code})")
            item.setData(Qt.ItemDataRole.UserRole, obj.code)
            self.list_widget.addItem(item)

    def _apply_filter(self):
        self._populate_list()

    def _on_item_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if not current:
            self.selected_code = None
            self.preview_label.clear()
            self.info_label.setText("Wybierz obiekt z listy")
            self.object_selected.emit(-1)
            return

        code = current.data(Qt.ItemDataRole.UserRole)
        self.selected_code = code
        obj = self.objects_lib.get_by_code(code)

        if obj:
            # Rysuj podgląd
            pix = self.renderer.render_object_pixmap(obj, zoom=4)
            self.preview_label.setPixmap(pix)

            flags_str = []
            if obj.flags.blocking:
                flags_str.append("blokujący")
            if obj.flags.interactive:
                flags_str.append("interaktywny")
            if obj.flags.secret:
                flags_str.append("sekret")
            flags_txt = ", ".join(flags_str) if flags_str else "brak"

            tags_txt = ", ".join(obj.tags) if obj.tags else "brak"

            info = (
                f"<b>{obj.id}</b> (kod: {obj.code})<br>"
                f"Rozmiar: {obj.size.width} × {obj.size.height} znaków<br>"
                f"Flagi: {flags_txt}<br>"
                f"Tagi: {tags_txt}"
            )
            self.info_label.setText(info)
            self.object_selected.emit(code)
