"""Obsługa ładowania i dekodowania charsetu Atari .fnt w trybie ANTIC Mode 4."""

from pathlib import Path
from typing import List, Union


class Charset:
    def __init__(self):
        self.data = bytearray(1024)
        self.is_loaded = False

    def load(self, path: Union[str, Path]) -> bool:
        """
        Wczytuje plik .fnt Atari.
        Wymaga co najmniej 1024 bajtów (128 znaków x 8 bajtów).
        """
        file_path = Path(path)
        if not file_path.exists():
            return False

        try:
            with open(file_path, "rb") as f:
                content = f.read()
                if len(content) < 1024:
                    return False
                self.data = bytearray(content[:1024])
                self.is_loaded = True
                return True
        except Exception:
            return False

    def get_tile_pixels(self, tile_index: int) -> List[List[int]]:
        """
        Zwraca matrycę 8x4 pikseli dla podanego indeksu znaku (0-255) w trybie ANTIC 4.
        Zwraca listę 8 wierszy, każdy wiersz to 4 liczby całkowite:
        0 = BACKGROUND
        1 = PF0
        2 = PF1
        3 = PF2
        4 = PF3_INV (gdy tile_index >= 128 i piksel ma wartość binarną %11)
        """
        if tile_index < 0 or tile_index > 255:
            tile_index = 0

        inverse = tile_index >= 128
        base_index = tile_index % 128

        offset = base_index * 8
        pixels: List[List[int]] = []

        for y in range(8):
            byte = self.data[offset + y]
            row: List[int] = []
            for x in range(4):
                shift = (3 - x) * 2
                val = (byte >> shift) & 0b11
                if val == 3 and inverse:
                    val = 4
                row.append(val)
            pixels.append(row)

        return pixels
