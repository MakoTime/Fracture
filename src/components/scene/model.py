from typing import Any


class SceneModel:
    """Collection of objects registered with the scene viewer."""

    def __init__(self):
        self.objects = []

    def add_object(self, object_base: Any):
        if object_base not in self.objects:
            self.objects.append(object_base)

    def remove_object(self, object_base: Any):
        if object_base not in self.objects:
            return False
        self.objects.remove(object_base)
        return True

    def clear(self):
        self.objects.clear()
