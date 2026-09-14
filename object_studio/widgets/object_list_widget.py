from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, 
    QHBoxLayout, QMenu, QComboBox, QLabel
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QAction, QIcon, QPixmap, QImage, QColor
from ..models import Project, ObjectDefinition
from ..charset import Charset
from ..settings import DEFAULT_COLORS

ALL_TAGS_OPTION = "(Wszystkie tagi)"
ORDER_CODE_OPTION = "Code"
ORDER_ID_OPTION = "ID (nazwa)"

class ObjectListWidget(QWidget):
    object_selected = Signal(ObjectDefinition)
    add_requested = Signal()
    delete_requested = Signal(ObjectDefinition)
    copy_requested = Signal(ObjectDefinition)
    shift_requested = Signal(ObjectDefinition, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.current_object = None
        self.filtered_objects = []
        self.charset: Optional[Charset] = None
        self.colors: List[QColor] = [QColor(*rgb) for rgb in DEFAULT_COLORS.values()]
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Kontrolki filtrowania i porządkowania
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(4)

        # Filtr tagów
        filter_layout = QHBoxLayout()
        lbl_filter = QLabel("Filtr:")
        lbl_filter.setFixedWidth(55)
        filter_layout.addWidget(lbl_filter)
        self.combo_tag_filter = QComboBox()
        self.combo_tag_filter.addItem(ALL_TAGS_OPTION)
        self.combo_tag_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.combo_tag_filter, 1)
        controls_layout.addLayout(filter_layout)

        # Porządkowanie (Order)
        order_layout = QHBoxLayout()
        lbl_order = QLabel("Kolejność:")
        lbl_order.setFixedWidth(55)
        order_layout.addWidget(lbl_order)
        self.combo_order = QComboBox()
        self.combo_order.addItem(ORDER_CODE_OPTION, "code")
        self.combo_order.addItem(ORDER_ID_OPTION, "id")
        self.combo_order.currentIndexChanged.connect(self._on_order_changed)
        order_layout.addWidget(self.combo_order, 1)
        controls_layout.addLayout(order_layout)

        layout.addLayout(controls_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("+ Dodaj")
        self.btn_add.clicked.connect(self.add_requested.emit)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_copy = QPushButton("Kopiuj")
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        btn_layout.addWidget(self.btn_copy)
        
        self.btn_del = QPushButton("- Usuń")
        self.btn_del.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self.btn_del)
        
        layout.addLayout(btn_layout)

    def set_project(self, project: Project):
        self.project = project
        self.current_object = None
        self.update_tag_filter_options()
        self.refresh_list()

    def update_tag_filter_options(self):
        current_text = self.combo_tag_filter.currentText()
        self.combo_tag_filter.blockSignals(True)
        self.combo_tag_filter.clear()
        self.combo_tag_filter.addItem(ALL_TAGS_OPTION)

        if self.project:
            for tag in self.project.available_tags:
                self.combo_tag_filter.addItem(tag)

        idx = self.combo_tag_filter.findText(current_text)
        if idx >= 0:
            self.combo_tag_filter.setCurrentIndex(idx)
        else:
            self.combo_tag_filter.setCurrentIndex(0)
        self.combo_tag_filter.blockSignals(False)

    def set_charset(self, charset: Optional[Charset]):
        self.charset = charset
        self.refresh_list(select_obj=self.current_object)

    def set_colors(self, color_dict):
        self.colors = [QColor(*rgb) for rgb in color_dict.values()]
        self.refresh_list(select_obj=self.current_object)

    def _render_icon(self, obj: ObjectDefinition) -> QIcon:
        if not self.charset or not getattr(self.charset, "data", None):
            return QIcon()

        w_chars = max(1, obj.size.width)
        h_chars = max(1, obj.size.height)
        px_w = w_chars * 8
        px_h = h_chars * 8

        img = QImage(px_w, px_h, QImage.Format.Format_ARGB32)
        bg_color = self.colors[0] if self.colors else QColor(0, 0, 0)
        img.fill(bg_color)

        tiles = obj.tiles
        tile_idx = 0
        for cy in range(h_chars):
            for cx in range(w_chars):
                if tile_idx < len(tiles):
                    t_val = tiles[tile_idx]
                    pixels = self.charset.get_tile_pixels(t_val)
                    for py in range(8):
                        row = pixels[py]
                        for px in range(4):
                            c_idx = row[px]
                            if 0 < c_idx < len(self.colors):
                                qc = self.colors[c_idx]
                                img.setPixelColor(cx * 8 + px * 2, cy * 8 + py, qc)
                                img.setPixelColor(cx * 8 + px * 2 + 1, cy * 8 + py, qc)
                tile_idx += 1

        pix = QPixmap.fromImage(img)
        max_dim = max(px_w, px_h)
        if max_dim > 0:
            scale = max(1, 32 // max_dim)
            if scale > 1:
                pix = pix.scaled(
                    px_w * scale,
                    px_h * scale,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )

        return QIcon(pix)

    def update_object_item(self, obj: ObjectDefinition):
        if not obj or obj not in self.filtered_objects:
            return
        idx = self.filtered_objects.index(obj)
        item = self.list_widget.item(idx)
        if item:
            tag_str = f" [{', '.join(obj.tags)}]" if obj.tags else ""
            item.setText(f"[{obj.code}] {obj.id}{tag_str}")
            item.setIcon(self._render_icon(obj))

    def _on_filter_changed(self, text):
        self.refresh_list(select_obj=self.current_object)

    def _on_order_changed(self, index: int):
        self.refresh_list(select_obj=self.current_object)
        
    def refresh_list(self, select_obj=None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.filtered_objects = []

        if not self.project:
            self.list_widget.blockSignals(False)
            return
            
        # Porządkowanie (Order) wg Code (domyślnie) lub ID (nazwy)
        order_mode = self.combo_order.currentData() if hasattr(self, "combo_order") else "code"
        if order_mode == "id":
            self.project.objects.sort(key=lambda x: (str(x.id).lower(), x.code))
        else:
            self.project.objects.sort(key=lambda x: (x.code, str(x.id).lower()))

        selected_tag = self.combo_tag_filter.currentText()
        
        for obj in self.project.objects:
            if selected_tag != ALL_TAGS_OPTION and selected_tag:
                if selected_tag not in obj.tags:
                    continue
            self.filtered_objects.append(obj)
            tag_str = f" [{', '.join(obj.tags)}]" if obj.tags else ""
            icon = self._render_icon(obj)
            item = QListWidgetItem(icon, f"[{obj.code}] {obj.id}{tag_str}")
            self.list_widget.addItem(item)
            
        self.list_widget.blockSignals(False)

        target_obj = select_obj or self.current_object
        if target_obj and target_obj in self.filtered_objects:
            self.current_object = target_obj
            idx = self.filtered_objects.index(self.current_object)
            self.list_widget.setCurrentRow(idx)
        elif self.filtered_objects:
            self.list_widget.setCurrentRow(0)
            self._on_selection_changed()
        else:
            self.current_object = None
            self.object_selected.emit(None)

    def _on_selection_changed(self):
        if not self.project:
            return
            
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.filtered_objects):
            self.current_object = self.filtered_objects[row]
            self.object_selected.emit(self.current_object)
        else:
            self.current_object = None
            self.object_selected.emit(None)

    def _on_delete_clicked(self):
        if self.current_object:
            self.delete_requested.emit(self.current_object)

    def _on_copy_clicked(self):
        if self.current_object:
            self.copy_requested.emit(self.current_object)

    def _on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item or not self.current_object:
            return
            
        menu = QMenu(self)
        
        act_up = menu.addAction("Shift Up")
        act_up.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'up'))
        
        act_down = menu.addAction("Shift Down")
        act_down.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'down'))
        
        act_left = menu.addAction("Shift Left")
        act_left.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'left'))
        
        act_right = menu.addAction("Shift Right")
        act_right.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'right'))
        
        menu.exec(self.list_widget.mapToGlobal(pos))
