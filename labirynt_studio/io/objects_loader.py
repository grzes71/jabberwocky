"""Wczytywanie i obsługa definicji obiektów z objects.yaml."""

from pathlib import Path
from typing import Dict, List, Tuple, Union
import yaml
from ..model.models import ObjectDefinition, ObjectSize, ObjectFlags


class ObjectsLibrary:
    def __init__(self):
        self.objects: List[ObjectDefinition] = []
        self.by_code: Dict[int, ObjectDefinition] = {}
        self.by_id: Dict[str, ObjectDefinition] = {}
        self.tags: List[str] = []
        self.is_loaded = False

    def load(self, path: Union[str, Path]) -> bool:
        file_path = Path(path)
        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            self.tags = list(data.get("tags", []))
            self.objects = []
            self.by_code = {}
            self.by_id = {}

            for obj_data in data.get("objects", []):
                size_data = obj_data.get("size", {})
                flags_data = obj_data.get("flags", {})
                obj_tags = [str(t) for t in obj_data.get("tags", [])]

                for t in obj_tags:
                    if t not in self.tags:
                        self.tags.append(t)

                obj_def = ObjectDefinition(
                    id=str(obj_data.get("id") or obj_data.get("object") or ""),
                    code=int(obj_data.get("code", 0)),
                    size=ObjectSize(
                        width=int(size_data.get("width", 2)),
                        height=int(size_data.get("height", 2)),
                    ),
                    flags=ObjectFlags(
                        blocking=bool(flags_data.get("blocking", False)),
                        interactive=bool(flags_data.get("interactive", False)),
                        secret=bool(flags_data.get("secret", False)),
                    ),
                    tiles=[int(t) for t in obj_data.get("tiles", [])],
                    tags=obj_tags,
                )

                self.objects.append(obj_def)
                self.by_code[obj_def.code] = obj_def
                if obj_def.id:
                    self.by_id[obj_def.id] = obj_def

            self.is_loaded = True
            return True
        except Exception:
            return False

    def get_by_code(self, code: int) -> ObjectDefinition | None:
        return self.by_code.get(code)

    def get_by_id(self, obj_id: str) -> ObjectDefinition | None:
        return self.by_id.get(obj_id)
