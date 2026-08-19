from typing import Any

import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .model import SceneModel


class SceneViewer(QWidget):
    """Qt widget that displays SceneModel objects with PyVista."""

    def __init__(self, parent=None, scene_model=None):
        super().__init__(parent)
        self.scene_model = scene_model or SceneModel()
        self._actors = {}
        self.plotter = QtInteractor(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotter.interactor)
        self.plotter.show_axes()

    def add_object(self, object_base: Any):
        payload = getattr(object_base, "scene_data", object_base)
        if payload is None:
            raise ValueError("ObjectBase.scene_data must contain PyVista data")

        name = getattr(object_base, "name", None)
        if hasattr(payload, "GetMapper"):
            actor = self.plotter.add_actor(payload, reset_camera=False)
        else:
            actor = self.plotter.add_mesh(payload, name=name, reset_camera=False)

        actor.SetVisibility(bool(getattr(object_base, "visible", True)))
        self._actors[object_base] = actor
        self.scene_model.add_object(object_base)
        self.plotter.render()
        return actor

    def remove_object(self, object_base: Any):
        actor = self._actors.pop(object_base, None)
        if actor is None:
            return False
        self.scene_model.remove_object(object_base)
        self.plotter.remove_actor(actor)
        self.plotter.render()
        return True

    def set_object_visibility(self, object_base: Any, visible: bool):
        actor = self._actors.get(object_base)
        if actor is None:
            return False
        actor.SetVisibility(bool(visible))
        self.plotter.render()
        return True

    def clear_scene(self):
        self.plotter.clear()
        self._actors.clear()
        self.scene_model.clear()
        self.plotter.show_axes()
        self.plotter.render()