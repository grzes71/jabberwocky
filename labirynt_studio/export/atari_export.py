"""Szkielet eksportera danych binarnego poziomu dla Atari 8-bit (LEVEL.BIN)."""

from pathlib import Path
from typing import Union, Tuple, Optional
from ..model.models import Project, Screen


def export_screen_to_binary(screen: Screen) -> bytes:
    """
    Eksportuje pojedynczy ekran do ciągu bajtów.
    Format 2-bajtowy na instancję:
    [Liczba obiektów (1 B)] + [Bajt 1: code, Bajt 2: packed_xy] * N
    """
    data = bytearray()
    data.append(len(screen.objects) & 0xFF)
    for inst in screen.objects:
        data.append(inst.code & 0xFF)
        data.append(inst.packed_xy & 0xFF)
    return bytes(data)


def export_labyrinth_binary(project: Project, labyrinth_id: str, out_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """Eksportuje wybrany labirynt do pliku binarnego."""
    lab = project.get_labyrinth(labyrinth_id)
    if not lab:
        return False, f"Nie znaleziono labiryntu: {labyrinth_id}"

    try:
        bin_data = bytearray()
        # Nagłówek: liczba ekranów
        bin_data.append(len(lab.screens) & 0xFF)

        for sid in lab.screens:
            screen = project.get_screen(sid)
            if not screen:
                return False, f"Brak definicji ekranu '{sid}' w projekcie"
            scr_bin = export_screen_to_binary(screen)
            bin_data.extend(scr_bin)

        with open(out_path, "wb") as f:
            f.write(bin_data)
        return True, None
    except Exception as e:
        return False, f"Błąd eksportu binarnego: {str(e)}"
