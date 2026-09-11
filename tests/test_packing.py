import pytest
from labirynt_studio.model.packing import pack_xy, unpack_xy, GRID_COLS, GRID_ROWS

def test_packing_extremes():
    """Test skrajnych pozycji: (0,0), (38,0), (0,10), (38,10)."""
    # (0, 0) -> x_half=0, y_half=0 -> packed=0
    assert pack_xy(0, 0) == 0
    assert unpack_xy(0) == (0, 0)

    # (38, 0) -> x_half=19, y_half=0 -> packed=19
    assert pack_xy(38, 0) == 19
    assert unpack_xy(19) == (38, 0)

    # (0, 10) -> x_half=0, y_half=5 -> packed=(5 << 5) = 160
    assert pack_xy(0, 10) == 160
    assert unpack_xy(160) == (0, 10)

    # (38, 10) -> x_half=19, y_half=5 -> packed=(5 << 5) | 19 = 179
    assert pack_xy(38, 10) == 179
    assert unpack_xy(179) == (38, 10)


def test_roundtrip_all_valid_combinations():
    """Weryfikacja pack(unpack(val)) == val oraz unpack(pack(x,y)) == (x,y) dla wszystkich 120 pozycji."""
    count = 0
    for y_half in range(GRID_ROWS):  # 0..5
        for x_half in range(GRID_COLS):  # 0..19
            x = x_half * 2
            y = y_half * 2
            packed = pack_xy(x, y)
            
            # Weryfikacja bitów
            assert (packed & 0x1F) == x_half
            assert (packed >> 5) == y_half
            
            # Weryfikacja unpack
            unpacked_x, unpacked_y = unpack_xy(packed)
            assert (unpacked_x, unpacked_y) == (x, y)
            
            # Weryfikacja pack(unpack(packed)) == packed
            assert pack_xy(*unpack_xy(packed)) == packed
            count += 1

    assert count == 120


def test_invalid_coordinates():
    """Testy obsługi błędów dla nieprawidłowych współrzędnych."""
    # Nieparzyste
    with pytest.raises(ValueError, match="podzielna przez 2"):
        pack_xy(1, 0)
    with pytest.raises(ValueError, match="podzielna przez 2"):
        pack_xy(0, 3)

    # Poza zakresem dodatnim
    with pytest.raises(ValueError, match="poza zakresem"):
        pack_xy(40, 0)
    with pytest.raises(ValueError, match="poza zakresem"):
        pack_xy(0, 12)

    # Ujemne
    with pytest.raises(ValueError, match="poza zakresem"):
        pack_xy(-2, 0)
    with pytest.raises(ValueError, match="poza zakresem"):
        pack_xy(0, -2)

    # Błędne typy
    with pytest.raises(TypeError):
        pack_xy(2.0, 0)  # type: ignore


def test_invalid_packed_values():
    """Wartości poza 0..255 lub nielegalne kombinacje bitowe."""
    with pytest.raises(ValueError):
        unpack_xy(-1)
    with pytest.raises(ValueError):
        unpack_xy(256)

    # x_half >= 20 (np. x_half = 25 -> packed = 25)
    with pytest.raises(ValueError, match="przekracza maksymalną liczbę kolumn"):
        unpack_xy(25)

    # y_half >= 6 (np. y_half = 6 -> packed = 6 << 5 = 192)
    with pytest.raises(ValueError, match="przekracza maksymalną liczbę wierszy"):
        unpack_xy(192)
