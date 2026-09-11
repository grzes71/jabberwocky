"""Silnik walidacji obiektów, ekranów i całego projektu."""

from dataclasses import dataclass
from typing import List, Optional
from ..model.models import Project, Screen, ObjectInstance
from ..model.packing import SCREEN_WIDTH_CHARS, SCREEN_HEIGHT_CHARS, GRID_STEP_X, GRID_STEP_Y
from ..io.objects_loader import ObjectsLibrary


@dataclass
class ValidationIssue:
    severity: str  # "ERROR" lub "WARNING"
    message: str
    screen_id: Optional[str] = None
    code: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None


class ProjectValidator:
    def __init__(self, objects_lib: ObjectsLibrary):
        self.objects_lib = objects_lib

    def validate_screen(self, screen: Screen) -> List[ValidationIssue]:
        """Waliduje pojedynczy ekran pod kątem obiektów, ich granic i kolizji."""
        issues: List[ValidationIssue] = []

        # Mapa zajętości kafelków dla kolizji blokujących: (cx, cy) -> instancja
        blocking_tiles = {}

        for inst in screen.objects:
            obj_def = self.objects_lib.get_by_code(inst.code)
            obj_name = obj_def.id if obj_def else f"CODE_{inst.code}"

            # 1. Czy kod obiektu istnieje w bazie
            if not obj_def:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message=f"Nieznany kod obiektu: {inst.code} na pozycji ({inst.x}, {inst.y})",
                    screen_id=screen.id,
                    code=inst.code,
                    x=inst.x,
                    y=inst.y,
                ))
                continue

            # 2. Czy pozycja leży na dozwolonej siatce 2x2
            if inst.x % GRID_STEP_X != 0 or inst.y % GRID_STEP_Y != 0:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message=f"Obiekt {obj_name} na pozycji ({inst.x}, {inst.y}) nie leży na siatce {GRID_STEP_X}x{GRID_STEP_Y}",
                    screen_id=screen.id,
                    code=inst.code,
                    x=inst.x,
                    y=inst.y,
                ))

            # 3. Czy obiekt mieści się na ekranie (40x11 znaków)
            w = obj_def.size.width
            h = obj_def.size.height

            if inst.x < 0 or inst.y < 0:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message=f"Obiekt {obj_name} ma ujemne współrzędne ({inst.x}, {inst.y})",
                    screen_id=screen.id,
                    code=inst.code,
                    x=inst.x,
                    y=inst.y,
                ))
            elif inst.x + w > SCREEN_WIDTH_CHARS or inst.y + h > SCREEN_HEIGHT_CHARS:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message=(
                        f"Obiekt {obj_name} na pozycji ({inst.x}, {inst.y}) o rozmiarze {w}x{h} "
                        f"wychodzi poza granice ekranu ({SCREEN_WIDTH_CHARS}x{SCREEN_HEIGHT_CHARS})"
                    ),
                    screen_id=screen.id,
                    code=inst.code,
                    x=inst.x,
                    y=inst.y,
                ))

            # 4. Sprawdzanie kolizji blokujących
            if obj_def.flags.blocking:
                for cy in range(inst.y, inst.y + h):
                    for cx in range(inst.x, inst.x + w):
                        coord = (cx, cy)
                        if coord in blocking_tiles:
                            other = blocking_tiles[coord]
                            other_def = self.objects_lib.get_by_code(other.code)
                            other_name = other_def.id if other_def else f"CODE_{other.code}"
                            issues.append(ValidationIssue(
                                severity="WARNING",
                                message=(
                                    f"Kolizja obiektów blokujących: {obj_name} ({inst.x}, {inst.y}) "
                                    f"oraz {other_name} ({other.x}, {other.y}) w punkcie {coord}"
                                ),
                                screen_id=screen.id,
                                code=inst.code,
                                x=inst.x,
                                y=inst.y,
                            ))
                        else:
                            blocking_tiles[coord] = inst

        return issues

    def validate_project(self, project: Project) -> List[ValidationIssue]:
        """Waliduje cały projekt: ekrany, labirynty, unikalność ID."""
        issues: List[ValidationIssue] = []

        # 1. Unikalność ID ekranów
        screen_ids = set()
        for screen in project.screens:
            if not screen.id.strip():
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message="Wykryto ekran z pustym ID",
                ))
            elif screen.id in screen_ids:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message=f"Zduplikowane ID ekranu: '{screen.id}'",
                    screen_id=screen.id,
                ))
            else:
                screen_ids.add(screen.id)

            # Walidacja zawartości ekranu
            issues.extend(self.validate_screen(screen))

        # 2. Walidacja labiryntów
        lab_ids = set()
        for lab in project.labyrinths:
            if not lab.id.strip():
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message="Wykryto labirynt z pustym ID",
                ))
            elif lab.id in lab_ids:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    message=f"Zduplikowane ID labiryntu: '{lab.id}'",
                ))
            else:
                lab_ids.add(lab.id)

            for sid in lab.screens:
                if sid not in screen_ids:
                    issues.append(ValidationIssue(
                        severity="ERROR",
                        message=f"Labirynt '{lab.id}' odwołuje się do nieznanego ekranu '{sid}'",
                    ))

        return issues
