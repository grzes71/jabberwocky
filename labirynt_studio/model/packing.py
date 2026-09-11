"""Obsługa pakowania i rozpakowywania pozycji obiektów na siatce ekranu Atari."""

from typing import Tuple

SCREEN_WIDTH_CHARS = 40
SCREEN_HEIGHT_CHARS = 11

GRID_STEP_X = 2
GRID_STEP_Y = 2

GRID_COLS = SCREEN_WIDTH_CHARS // GRID_STEP_X  # 20 kolumn: 0..19
GRID_ROWS = (SCREEN_HEIGHT_CHARS + 1) // GRID_STEP_Y  # 6 wierszy: 0..5 (y=0, 2, 4, 6, 8, 10)


def pack_xy(x: int, y: int) -> int:
    """
    Pakuje współrzędne ekranu (x, y) do jednego bajtu (packed_xy).
    
    x: 0, 2, 4, ..., 38 (x_half: 0..19)
    y: 0, 2, 4, ..., 10 (y_half: 0..5)
    
    Bit 7 6 5 | 4 3 2 1 0
        Y     |    X
    """
    if not isinstance(x, int) or not isinstance(y, int):
        raise TypeError(f"Współrzędne muszą być liczbami całkowitymi, otrzymano: x={type(x)}, y={type(y)}")

    if x % GRID_STEP_X != 0:
        raise ValueError(f"Współrzędna x={x} musi być podzielna przez {GRID_STEP_X}")
    if y % GRID_STEP_Y != 0:
        raise ValueError(f"Współrzędna y={y} musi być podzielna przez {GRID_STEP_Y}")

    x_half = x // GRID_STEP_X
    y_half = y // GRID_STEP_Y

    if not (0 <= x_half < GRID_COLS):
        raise ValueError(f"Współrzędna x={x} (x_half={x_half}) poza zakresem 0..{GRID_COLS - 1}")
    if not (0 <= y_half < GRID_ROWS):
        raise ValueError(f"Współrzędna y={y} (y_half={y_half}) poza zakresem 0..{GRID_ROWS - 1}")

    return (y_half << 5) | x_half


def unpack_xy(packed_xy: int) -> Tuple[int, int]:
    """
    Rozpakowuje bajt packed_xy do współrzędnych ekranowych (x, y).
    """
    if not isinstance(packed_xy, int):
        raise TypeError(f"Wartość packed_xy musi być liczbą całkowitą, otrzymano: {type(packed_xy)}")
    if not (0 <= packed_xy <= 255):
        raise ValueError(f"packed_xy={packed_xy} musi mieścić się w zakresie bajtu (0..255)")

    x_half = packed_xy & 0x1F
    y_half = (packed_xy >> 5) & 0x07

    if x_half >= GRID_COLS:
        raise ValueError(f"Rozpakowany x_half={x_half} przekracza maksymalną liczbę kolumn {GRID_COLS}")
    if y_half >= GRID_ROWS:
        raise ValueError(f"Rozpakowany y_half={y_half} przekracza maksymalną liczbę wierszy {GRID_ROWS}")

    x = x_half << 1
    y = y_half << 1
    return x, y


def snap_coordinate(val: int, step: int = 2) -> int:
    """Zaokrągla współrzędną w dół lub do najbliższej siatki."""
    return (val // step) * step
