"""Silnik renderowania grafiki Atari ANTIC Mode 4 dla kafelków, obiektów i ekranów."""

from typing import Optional, Dict
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QRect

from .charset import Charset
from .palette import AtariPalette
from ..model.models import ObjectDefinition, Screen, ObjectInstance
from ..io.objects_loader import ObjectsLibrary

# Standardowa geometria ekranu Atari (40x11 znaków w trybie ANTIC 4/5)
SCREEN_WIDTH_CHARS = 40
SCREEN_HEIGHT_CHARS = 11

CHAR_PIXEL_WIDTH = 8   # 8 pikseli ekranowych (4 piksele barwne, każdy o szerokości 2)
CHAR_PIXEL_HEIGHT = 8  # 8 linii rastra

SCREEN_WIDTH_PIXELS = SCREEN_WIDTH_CHARS * CHAR_PIXEL_WIDTH   # 320 px
SCREEN_HEIGHT_PIXELS = SCREEN_HEIGHT_CHARS * CHAR_PIXEL_HEIGHT # 88 px


class AtariRenderer:
    def __init__(self, charset: Charset, palette: AtariPalette):
        self.charset = charset
        self.palette = palette

    def render_tile_image(self, tile_index: int) -> QImage:
        """
        Renderuje pojedynczy kafelek znaku (8x8 pikseli ekranowych, 4x8 pikseli barwnych).
        """
        img = QImage(CHAR_PIXEL_WIDTH, CHAR_PIXEL_HEIGHT, QImage.Format.Format_ARGB32)
        bg_rgb = self.palette.get_rgb(0)
        img.fill(QColor(*bg_rgb))

        if not self.charset.is_loaded:
            return img

        pixels = self.charset.get_tile_pixels(tile_index)
        for y in range(8):
            row = pixels[y]
            for x in range(4):
                color_idx = row[x]
                if color_idx > 0:
                    r, g, b = self.palette.get_rgb(color_idx)
                    qc = QColor(r, g, b)
                    # Każdy piksel barwny ma szerokość 2 pikseli ekranowych
                    img.setPixelColor(x * 2, y, qc)
                    img.setPixelColor(x * 2 + 1, y, qc)

        return img

    def render_object_image(self, obj_def: ObjectDefinition) -> QImage:
        """
        Renderuje obiekt na podstawie jego wymiarów (w znakach) i listy tiles.
        """
        w_chars = max(1, obj_def.size.width)
        h_chars = max(1, obj_def.size.height)
        px_w = w_chars * CHAR_PIXEL_WIDTH
        px_h = h_chars * CHAR_PIXEL_HEIGHT

        img = QImage(px_w, px_h, QImage.Format.Format_ARGB32)
        bg_rgb = self.palette.get_rgb(0)
        img.fill(QColor(*bg_rgb))

        tiles = obj_def.tiles
        tile_idx = 0
        for cy in range(h_chars):
            for cx in range(w_chars):
                if tile_idx < len(tiles):
                    t_val = tiles[tile_idx]
                    tile_img = self.render_tile_image(t_val)
                    # Kopiuj piksele kafelka do obrazu obiektu
                    for py in range(CHAR_PIXEL_HEIGHT):
                        for px in range(CHAR_PIXEL_WIDTH):
                            c = tile_img.pixelColor(px, py)
                            img.setPixelColor(cx * CHAR_PIXEL_WIDTH + px, cy * CHAR_PIXEL_HEIGHT + py, c)
                tile_idx += 1

        return img

    def render_object_pixmap(self, obj_def: ObjectDefinition, zoom: int = 2) -> QPixmap:
        """Renderuje obiekt bezpośrednio do QPixmap z uwzględnieniem powiększenia."""
        img = self.render_object_image(obj_def)
        pix = QPixmap.fromImage(img)
        if zoom != 1:
            pix = pix.scaled(pix.width() * zoom, pix.height() * zoom, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        return pix

    def render_screen_image(
        self,
        screen: Screen,
        objects_lib: ObjectsLibrary,
        mode: str = "ATARI"
    ) -> QImage:
        """
        Renderuje cały ekran 40x11 (320x88 pikseli).
        """
        img = QImage(SCREEN_WIDTH_PIXELS, SCREEN_HEIGHT_PIXELS, QImage.Format.Format_ARGB32)
        bg_rgb = self.palette.get_rgb(0)
        img.fill(QColor(*bg_rgb))

        # Rysuj obiekty
        for inst in screen.objects:
            obj_def = objects_lib.get_by_code(inst.code)
            if not obj_def:
                continue

            obj_img = self.render_object_image(obj_def)
            start_px = inst.x * CHAR_PIXEL_WIDTH
            start_py = inst.y * CHAR_PIXEL_HEIGHT

            for oy in range(obj_img.height()):
                target_y = start_py + oy
                if target_y >= SCREEN_HEIGHT_PIXELS:
                    break
                for ox in range(obj_img.width()):
                    target_x = start_px + ox
                    if target_x >= SCREEN_WIDTH_PIXELS:
                        break
                    # Pomiń tło jeśli obiekt nie jest pełny lub rysuj bezpośrednio
                    c = obj_img.pixelColor(ox, oy)
                    img.setPixelColor(target_x, target_y, c)

        return img
