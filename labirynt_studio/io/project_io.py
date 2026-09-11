"""Zapis i odczyt całego projektu do/z pliku YAML."""

import os
from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple
import yaml

from ..model.models import Project, ProjectResources, Screen, ObjectInstance, Labyrinth
from ..model.packing import pack_xy, unpack_xy


def load_project_from_yaml(path: Union[str, Path]) -> Tuple[Optional[Project], Optional[str]]:
    """
    Wczytuje projekt z pliku YAML.
    Zwraca krotkę (Project, None) w przypadku sukcesu lub (None, error_msg) w przypadku błędu.
    """
    file_path = Path(path).resolve()
    if not file_path.exists():
        return None, f"Plik projektu nie istnieje: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return None, "Niepoprawna struktura pliku YAML (wymagany słownik)."

        proj_info = data.get("project", {})
        proj_name = proj_info.get("name", "Jabberwocky")

        # Zasoby
        res_data = data.get("resources", {})
        resources = ProjectResources(
            objects=str(res_data.get("objects", "world/objects.yaml")),
            colors=str(res_data.get("colors", "world/colors.yaml")),
            charset=str(res_data.get("charset", "fonts/game.fnt")),
        )

        # Ekrany
        screens = []
        for s_data in data.get("screens", []):
            screen_id = str(s_data.get("id", ""))
            objects = []
            for obj_item in s_data.get("objects", []):
                code = int(obj_item.get("code", 0))
                if "packed_xy" in obj_item:
                    x, y = unpack_xy(int(obj_item["packed_xy"]))
                else:
                    x = int(obj_item.get("x", 0))
                    y = int(obj_item.get("y", 0))
                objects.append(ObjectInstance(code=code, x=x, y=y))
            screens.append(Screen(id=screen_id, objects=objects))

        # Labirynty
        labyrinths = []
        for l_data in data.get("labyrinths", []):
            lab_id = str(l_data.get("id", ""))
            lab_name = str(l_data.get("name", ""))
            lab_screens = [str(sid) for sid in l_data.get("screens", [])]
            labyrinths.append(Labyrinth(id=lab_id, name=lab_name, screens=lab_screens))

        project = Project(
            name=proj_name,
            resources=resources,
            screens=screens,
            labyrinths=labyrinths
        )
        return project, None
    except Exception as e:
        return None, f"Błąd podczas wczytywania projektu: {str(e)}"


def save_project_to_yaml(project: Project, path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None) -> Tuple[bool, Optional[str]]:
    """
    Zapisuje projekt do pliku YAML.
    Ścieżki do zasobów zapisywane są względnie do katalogu projektu.
    """
    file_path = Path(path).resolve()
    target_dir = file_path.parent

    # Oblicz ścieżki względne do zasobów
    def make_rel(p_str: str) -> str:
        p = Path(p_str)
        if not p.is_absolute():
            return p_str.replace("\\", "/")
        try:
            return os.path.relpath(p, target_dir).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    data: Dict[str, Any] = {
        "project": {
            "name": project.name,
        },
        "resources": {
            "objects": make_rel(project.resources.objects),
            "colors": make_rel(project.resources.colors),
            "charset": make_rel(project.resources.charset),
        },
        "screens": [],
        "labyrinths": []
    }

    for screen in project.screens:
        screen_data = {
            "id": screen.id,
            "objects": [
                {"code": inst.code, "packed_xy": inst.packed_xy}
                for inst in screen.objects
            ]
        }
        data["screens"].append(screen_data)

    for lab in project.labyrinths:
        lab_data = {
            "id": lab.id,
            "name": lab.name,
            "screens": list(lab.screens)
        }
        data["labyrinths"].append(lab_data)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, indent=2, allow_unicode=True)
        return True, None
    except Exception as e:
        return False, f"Błąd zapisu pliku: {str(e)}"
