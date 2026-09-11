"""Struktury danych modelu dla Labirynt Studio."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .packing import pack_xy, unpack_xy


@dataclass
class ObjectSize:
    width: int = 2
    height: int = 2


@dataclass
class ObjectFlags:
    blocking: bool = False
    interactive: bool = False
    secret: bool = False


@dataclass
class ObjectDefinition:
    id: str
    code: int
    size: ObjectSize = field(default_factory=ObjectSize)
    flags: ObjectFlags = field(default_factory=ObjectFlags)
    tiles: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class ObjectInstance:
    code: int
    x: int
    y: int

    @property
    def packed_xy(self) -> int:
        return pack_xy(self.x, self.y)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "packed_xy": self.packed_xy
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectInstance":
        code = int(data.get("code", 0))
        if "packed_xy" in data:
            x, y = unpack_xy(int(data["packed_xy"]))
        else:
            x = int(data.get("x", 0))
            y = int(data.get("y", 0))
        return cls(code=code, x=x, y=y)


@dataclass
class Screen:
    id: str
    objects: List[ObjectInstance] = field(default_factory=list)

    def get_object_at(self, x: int, y: int, object_defs: Optional[Dict[int, ObjectDefinition]] = None) -> Optional[ObjectInstance]:
        """Zwraca instancję obiektu pokrywającą podany punkt (x, y) w znakach."""
        for inst in reversed(self.objects):
            w, h = 2, 2
            if object_defs and inst.code in object_defs:
                obj_def = object_defs[inst.code]
                w = obj_def.size.width
                h = obj_def.size.height
            if inst.x <= x < inst.x + w and inst.y <= y < inst.y + h:
                return inst
        return None


@dataclass
class Labyrinth:
    id: str
    name: str = ""
    screens: List[str] = field(default_factory=list)


@dataclass
class ProjectResources:
    objects: str = "objects.yaml"
    colors: str = "colors.yaml"
    charset: str = "game.fnt"


@dataclass
class Project:
    name: str = "Jabberwocky"
    resources: ProjectResources = field(default_factory=ProjectResources)
    screens: List[Screen] = field(default_factory=list)
    labyrinths: List[Labyrinth] = field(default_factory=list)

    def get_screen(self, screen_id: str) -> Optional[Screen]:
        for s in self.screens:
            if s.id == screen_id:
                return s
        return None

    def add_screen(self, screen: Screen) -> None:
        self.screens.append(screen)

    def remove_screen(self, screen_id: str) -> bool:
        for idx, s in enumerate(self.screens):
            if s.id == screen_id:
                self.screens.pop(idx)
                # Usunięcie odwołań z labiryntów
                for lab in self.labyrinths:
                    lab.screens = [sid for sid in lab.screens if sid != screen_id]
                return True
        return False

    def duplicate_screen(self, source_id: str, new_id: str) -> Optional[Screen]:
        source = self.get_screen(source_id)
        if not source:
            return None
        new_objects = [ObjectInstance(code=obj.code, x=obj.x, y=obj.y) for obj in source.objects]
        new_screen = Screen(id=new_id, objects=new_objects)
        self.screens.append(new_screen)
        return new_screen

    def get_labyrinth(self, lab_id: str) -> Optional[Labyrinth]:
        for lab in self.labyrinths:
            if lab.id == lab_id:
                return lab
        return None
