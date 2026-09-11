"""Okno dialogowe wyboru i konfiguracji ścieżek do zasobów (objects, colors, charset)."""

from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QMessageBox
)


class ResourceDialog(QDialog):
    def __init__(
        self,
        objects_path: str = "world/objects.yaml",
        colors_path: str = "world/colors.yaml",
        charset_path: str = "fonts/game.fnt",
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Konfiguracja zasobów projektu")
        self.resize(560, 200)

        self._init_ui(objects_path, colors_path, charset_path)

    def _init_ui(self, obj_p: str, col_p: str, chr_p: str):
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        # Objects
        grid.addWidget(QLabel("Definicje obiektów (YAML):"), 0, 0)
        self.objects_edit = QLineEdit(obj_p)
        grid.addWidget(self.objects_edit, 0, 1)
        btn_obj = QPushButton("Przeglądaj...")
        btn_obj.clicked.connect(self._browse_objects)
        grid.addWidget(btn_obj, 0, 2)

        # Colors
        grid.addWidget(QLabel("Kolory Atari (YAML):"), 1, 0)
        self.colors_edit = QLineEdit(col_p)
        grid.addWidget(self.colors_edit, 1, 1)
        btn_col = QPushButton("Przeglądaj...")
        btn_col.clicked.connect(self._browse_colors)
        grid.addWidget(btn_col, 1, 2)

        # Charset
        grid.addWidget(QLabel("Charset Atari (.fnt):"), 2, 0)
        self.charset_edit = QLineEdit(chr_p)
        grid.addWidget(self.charset_edit, 2, 1)
        btn_chr = QPushButton("Przeglądaj...")
        btn_chr.clicked.connect(self._browse_charset)
        grid.addWidget(btn_chr, 2, 2)

        layout.addLayout(grid)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _browse_objects(self):
        f, _ = QFileDialog.getOpenFileName(self, "Wybierz plik objects.yaml", "", "YAML (*.yaml *.yml)")
        if f:
            self.objects_edit.setText(f)

    def _browse_colors(self):
        f, _ = QFileDialog.getOpenFileName(self, "Wybierz plik colors.yaml", "", "YAML (*.yaml *.yml)")
        if f:
            self.colors_edit.setText(f)

    def _browse_charset(self):
        f, _ = QFileDialog.getOpenFileName(self, "Wybierz plik charsetu .fnt", "", "Charset Atari (*.fnt *.bin)")
        if f:
            self.charset_edit.setText(f)

    def _validate_and_accept(self):
        p_obj = Path(self.objects_edit.text().strip())
        p_col = Path(self.colors_edit.text().strip())
        p_chr = Path(self.charset_edit.text().strip())

        missing = []
        if not p_obj.exists():
            missing.append(f"Nie odnaleziono pliku obiektów: {p_obj}")
        if not p_col.exists():
            missing.append(f"Nie odnaleziono pliku kolorów: {p_col}")
        if not p_chr.exists():
            missing.append(f"Nie odnaleziono pliku charsetu: {p_chr}")

        if missing:
            QMessageBox.warning(self, "Brakujące pliki", "\n".join(missing))
            return

        self.accept()

    def get_paths(self) -> Tuple[str, str, str]:
        return (
            self.objects_edit.text().strip(),
            self.colors_edit.text().strip(),
            self.charset_edit.text().strip(),
        )
