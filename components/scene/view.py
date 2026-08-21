from typing import Any

import numpy as np
import pyvista as pv
import vtk
from pyvistaqt import QtInteractor
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .model import SceneModel
from .sky_dome import SkyDome


class SceneViewer(QWidget):
    """Qt widget that displays SceneModel objects with PyVista."""

    def __init__(self, parent=None, scene_model=None):
        super().__init__(parent)
        self.scene_model = scene_model or SceneModel()
        self._actors = {}
        self.sky_dome = SkyDome()
        self.plotter = QtInteractor(self)
        self._pan_anchor = None
        self._pan_active = False
        self._pan_render_pending = False
        self.plotter.interactor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._configure_terrain_interaction()
        self.plotter.interactor.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotter.interactor)
        self.plotter.set_background("#465568")
        self.sky_dome.add_to(self.plotter)
        self._restore_lighting()
        self.plotter.show_axes()

    def _configure_terrain_interaction(self):
        """Use VTK's terrain navigation for orbit, pan, and zoom."""
        vtk.vtkObject.GlobalWarningDisplayOff()
        self._terrain_style = vtk.vtkInteractorStyleTerrain()
        self._terrain_style.SetDefaultRenderer(self.plotter.renderer)
        self.plotter.interactor.SetInteractorStyle(self._terrain_style)

    def _restore_lighting(self):
        """Restore the default three-point lighting after renderer resets."""
        self.plotter.enable_3_lights()

    def eventFilter(self, watched, event):
        if watched is not self.plotter.interactor:
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.MouseMove:
            if event.buttons() == (
                Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
            ):
                self._pan_camera(event.position().toPoint())
                return True
            self._pan_anchor = None

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.buttons() == (
                Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
            ):
                self._pan_active = True
                self._pan_anchor = event.position().toPoint()
                self._end_terrain_gesture()
                return True

        if event.type() == QEvent.Type.MouseButtonRelease and self._pan_active:
            self._pan_active = False
            self._pan_anchor = None
            self._end_terrain_gesture()
            self.plotter.render()
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            self._end_terrain_gesture()
            self.plotter.render()
        return super().eventFilter(watched, event)

    def _end_terrain_gesture(self):
        self._terrain_style.EndRotate()
        self._terrain_style.EndPan()

    def reset_camera(self):
        """Fit all visible scene data in the render window."""
        self.plotter.reset_camera()
        self.plotter.camera.SetClippingRange(
            0.01, self.sky_dome.radius * 2.0
        )
        self.plotter.render()

    def _pan_camera(self, position):
        if self._pan_anchor is None:
            self._pan_anchor = position
            return

        delta = position - self._pan_anchor
        movement = self._display_delta_to_world(delta)
        camera = self.plotter.camera
        camera.SetPosition(camera.GetPosition() + movement)
        camera.SetFocalPoint(camera.GetFocalPoint() + movement)
        self._pan_anchor = position
        self._schedule_pan_render()

    def _schedule_pan_render(self):
        if self._pan_render_pending:
            return
        self._pan_render_pending = True
        QTimer.singleShot(16, self._render_pan_frame)

    def _render_pan_frame(self):
        self._pan_render_pending = False
        self.plotter.render()

    def _display_delta_to_world(self, delta):
        camera = self.plotter.camera
        height = max(self.plotter.interactor.height(), 1)
        direction = np.asarray(camera.GetFocalPoint()) - np.asarray(
            camera.GetPosition()
        )
        direction /= np.linalg.norm(direction)
        view_up = np.asarray(camera.GetViewUp())
        view_up /= np.linalg.norm(view_up)
        right = np.cross(direction, view_up)
        right /= np.linalg.norm(right)
        screen_up = np.cross(right, direction)

        if camera.GetParallelProjection():
            world_height = 2.0 * camera.GetParallelScale()
        else:
            distance = np.linalg.norm(
                np.asarray(camera.GetFocalPoint())
                - np.asarray(camera.GetPosition())
            )
            world_height = 2.0 * distance * np.tan(
                np.deg2rad(camera.GetViewAngle()) / 2.0
            )

        pixels_to_world = world_height / height
        return pixels_to_world * (
            -delta.x() * right + delta.y() * screen_up
        )

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
        self.sky_dome.remove()
        self.sky_dome.add_to(self.plotter)
        self._restore_lighting()
        self._actors.clear()
        self.scene_model.clear()
        self.plotter.show_axes()
        self.plotter.render()