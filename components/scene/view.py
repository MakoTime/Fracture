from typing import Any

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .model import SceneModel


class SceneViewer(QWidget):
    """Qt widget that displays SceneModel objects with PyVista."""

    def __init__(self, parent=None, scene_model=None):
        super().__init__(parent)
        self.scene_model = scene_model or SceneModel()
        self._actors = {}
        self.plotter = QtInteractor(self)
        self._pan_anchor = None
        self._pan_render_pending = False
        self.plotter.interactor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.plotter.interactor.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotter.interactor)
        self._restore_lighting()
        self.plotter.show_axes()
        self._keep_z_vertical()

    def _restore_lighting(self):
        """Restore the default three-point lighting after renderer resets."""
        self.plotter.enable_3_lights()

    def eventFilter(self, watched, event):
        if watched is not self.plotter.interactor:
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Home:
                self.reset_camera()
                return True

        if event.type() == QEvent.Type.MouseMove:
            if event.buttons() == (
                Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
            ):
                self._pan_camera(event.position().toPoint())
                return True
            self._pan_anchor = None

        if event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
        ):
            if event.buttons() == (
                Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
            ):
                self._pan_anchor = event.position().toPoint()
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._pan_anchor = None

        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            self._keep_z_vertical()
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.plotter.render()
        return super().eventFilter(watched, event)

    def reset_camera(self):
        """Fit all visible scene data in the render window."""
        self.plotter.reset_camera()
        self._keep_z_vertical()
        self.plotter.render()

    def _keep_z_vertical(self):
        """Keep the world Z axis vertical while the camera moves."""
        self.plotter.camera.SetViewUp(0.0, 0.0, 1.0)

    def _pan_camera(self, position):
        if self._pan_anchor is None:
            self._pan_anchor = position
            return

        previous_world = self._display_to_focal_world(self._pan_anchor)
        current_world = self._display_to_focal_world(position)
        if previous_world is None or current_world is None:
            self._pan_anchor = position
            return

        movement = previous_world - current_world
        camera = self.plotter.camera
        camera.SetPosition(camera.GetPosition() + movement)
        camera.SetFocalPoint(camera.GetFocalPoint() + movement)
        self._pan_anchor = position
        self._keep_z_vertical()
        self._schedule_pan_render()

    def _schedule_pan_render(self):
        """Coalesce expensive VTK renders while the camera is being dragged."""
        if self._pan_render_pending:
            return
        self._pan_render_pending = True
        QTimer.singleShot(16, self._render_pan_frame)

    def _render_pan_frame(self):
        self._pan_render_pending = False
        self.plotter.render()

    def _display_to_focal_world(self, position):
        renderer = self.plotter.renderer
        camera = self.plotter.camera
        renderer.SetWorldPoint(*camera.GetFocalPoint(), 1.0)
        renderer.WorldToDisplay()
        focal_display = renderer.GetDisplayPoint()
        renderer.SetDisplayPoint(
            position.x(),
            self.plotter.interactor.height() - position.y(),
            focal_display[2],
        )
        renderer.DisplayToWorld()
        world = renderer.GetWorldPoint()
        if world[3] == 0:
            return None
        return np.asarray(world[:3], dtype=float)

    def add_object(self, object_base: Any):
        block_object = getattr(object_base, "block_object", None)
        payload = getattr(block_object, "scene_data", object_base)
        if payload is None:
            raise ValueError("ObjectBase.scene_data must contain PyVista data")

        if isinstance(payload, pv.StructuredGrid):
            payload = payload.extract_surface(
                algorithm="dataset_surface",
            ).compute_normals(
                auto_orient_normals=True,
                split_vertices=False,
                inplace=False,
            )
            if block_object is not None:
                block_object.mesh_data = payload

        name = getattr(object_base, "name", None)
        if hasattr(payload, "GetMapper"):
            actor = self.plotter.add_actor(payload, reset_camera=False)
        else:
            actor = self.plotter.add_mesh(
                payload,
                name=name,
                reset_camera=False,
            )

        actor.SetVisibility(bool(getattr(object_base, "visible", True)))
        self._actors[object_base] = actor
        self.scene_model.add_object(object_base)
        self.reset_camera()
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
        self._restore_lighting()
        self._actors.clear()
        self.scene_model.clear()
        self.plotter.show_axes()
        self.plotter.render()