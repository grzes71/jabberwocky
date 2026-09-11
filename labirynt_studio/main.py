"""Punkt wejścia aplikacji Labirynt Studio."""

import sys
import argparse
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont

from .ui.main_window import MainWindow
from .ui.resource_dialog import ResourceDialog


def parse_args():
    parser = argparse.ArgumentParser(
        description="Labirynt Studio — Narzędzie GUI do projektowania ekranów i labiryntów dla Atari 8-bit."
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
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Ścieżka do pliku projektu .yaml do otwarcia"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Ustawienie estetycznego fontu systemowego
    font = app.font()
    font.setPointSize(9)
    app.setFont(font)

    obj_path = args.objects
    col_path = args.colors
    chr_path = args.charset

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
        else:
            sys.exit(0)

    # Utworzenie i pokazanie głównego okna
    window = MainWindow(
        objects_path=obj_path,
        colors_path=col_path,
        charset_path=chr_path,
        project_path=args.project
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
