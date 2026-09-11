"""Polecenia edycyjne dla obsługi mechanizmu Undo/Redo (QUndoCommand)."""

from typing import Callable, List, Optional
from PySide6.QtGui import QUndoCommand
from .models import Screen, ObjectInstance


class AddObjectCommand(QUndoCommand):
    def __init__(self, screen: Screen, instance: ObjectInstance, on_change: Optional[Callable[[], None]] = None):
        super().__init__(f"Dodaj obiekt {instance.code} na ({instance.x}, {instance.y})")
        self.screen = screen
        self.instance = instance
        self.on_change = on_change

    def redo(self):
        self.screen.objects.append(self.instance)
        if self.on_change:
            self.on_change()

    def undo(self):
        if self.instance in self.screen.objects:
            self.screen.objects.remove(self.instance)
        if self.on_change:
            self.on_change()


class RemoveObjectCommand(QUndoCommand):
    def __init__(self, screen: Screen, instance: ObjectInstance, on_change: Optional[Callable[[], None]] = None):
        super().__init__(f"Usuń obiekt {instance.code} z ({instance.x}, {instance.y})")
        self.screen = screen
        self.instance = instance
        self.index = screen.objects.index(instance) if instance in screen.objects else -1
        self.on_change = on_change

    def redo(self):
        if self.instance in self.screen.objects:
            self.screen.objects.remove(self.instance)
        if self.on_change:
            self.on_change()

    def undo(self):
        if 0 <= self.index <= len(self.screen.objects):
            self.screen.objects.insert(self.index, self.instance)
        else:
            self.screen.objects.append(self.instance)
        if self.on_change:
            self.on_change()


class MoveObjectCommand(QUndoCommand):
    def __init__(
        self,
        screen: Screen,
        instance: ObjectInstance,
        old_x: int,
        old_y: int,
        new_x: int,
        new_y: int,
        on_change: Optional[Callable[[], None]] = None
    ):
        super().__init__(f"Przesuń obiekt {instance.code} z ({old_x}, {old_y}) do ({new_x}, {new_y})")
        self.screen = screen
        self.instance = instance
        self.old_x = old_x
        self.old_y = old_y
        self.new_x = new_x
        self.new_y = new_y
        self.on_change = on_change

    def redo(self):
        self.instance.x = self.new_x
        self.instance.y = self.new_y
        if self.on_change:
            self.on_change()

    def undo(self):
        self.instance.x = self.old_x
        self.instance.y = self.old_y
        if self.on_change:
            self.on_change()


class PasteObjectsCommand(QUndoCommand):
    def __init__(self, screen: Screen, instances: List[ObjectInstance], on_change: Optional[Callable[[], None]] = None):
        super().__init__(f"Wklej {len(instances)} obiektów")
        self.screen = screen
        self.instances = [ObjectInstance(code=inst.code, x=inst.x, y=inst.y) for inst in instances]
        self.on_change = on_change

    def redo(self):
        self.screen.objects.extend(self.instances)
        if self.on_change:
            self.on_change()

    def undo(self):
        for inst in self.instances:
            if inst in self.screen.objects:
                self.screen.objects.remove(inst)
        if self.on_change:
            self.on_change()
