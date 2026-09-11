"""Obsługa palety kolorów Atari pobieranej z pliku YAML."""

from pathlib import Path
from typing import Dict, List, Tuple, Union
import yaml
from PySide6.QtGui import QColor

# Domyślne wartości zapasowe
DEFAULT_RGB_PALETTE: Dict[str, Tuple[int, int, int]] = {
    "BACKGROUND": (0, 0, 0),
    "PF0": (140, 70, 0),
    "PF1": (236, 130, 0),
    "PF2": (0, 85, 0),
    "PF3_INV": (0, 0, 176),
}

REGISTER_ORDER = ["BACKGROUND", "PF0", "PF1", "PF2", "PF3_INV"]


class AtariPalette:
    def __init__(self):
        self.raw_rgb: Dict[str, Tuple[int, int, int]] = dict(DEFAULT_RGB_PALETTE)
        self.colors: List[QColor] = [QColor(*self.raw_rgb[reg]) for reg in REGISTER_ORDER]
        self.is_loaded = False

    def load(self, path: Union[str, Path]) -> bool:
        """Wczytuje plik colors.yaml."""
        file_path = Path(path)
        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return False

            new_raw: Dict[str, Tuple[int, int, int]] = {}
            for reg in REGISTER_ORDER:
                if reg in data and "rgb" in data[reg]:
                    rgb_list = data[reg]["rgb"]
                    if len(rgb_list) == 3:
                        new_raw[reg] = (int(rgb_list[0]), int(rgb_list[1]), int(rgb_list[2]))
                    else:
                        new_raw[reg] = DEFAULT_RGB_PALETTE[reg]
                else:
                    new_raw[reg] = DEFAULT_RGB_PALETTE[reg]

            self.raw_rgb = new_raw
            self.colors = [QColor(*self.raw_rgb[reg]) for reg in REGISTER_ORDER]
            self.is_loaded = True
            return True
        except Exception:
            return False

    def get_qcolor(self, index: int) -> QColor:
        """Zwraca QColor dla indeksu 0..4."""
        if 0 <= index < len(self.colors):
            return self.colors[index]
        return self.colors[0]

    def get_rgb(self, index: int) -> Tuple[int, int, int]:
        """Zwraca (r, g, b) dla indeksu 0..4."""
        reg = REGISTER_ORDER[index] if 0 <= index < len(REGISTER_ORDER) else REGISTER_ORDER[0]
        return self.raw_rgb[reg]
