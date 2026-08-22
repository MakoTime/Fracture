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

    def __init__(self, parent=None, scene_model=None, show_sky_dome=True):
        super().__init__(parent)
        self.scene_model = scene_model or SceneModel()
        self._actors = {}
        self._shape_actors = {}
        self._show_sky_dome = show_sky_dome
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
        if self._show_sky_dome:
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

        if event.type() == QEvent.Type.Wheel:
            self._zoom_camera_from_wheel(event.angleDelta().y())
            return True

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
            self._reset_clipping_range()
            self.plotter.render()
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            self._end_terrain_gesture()
            self._reset_clipping_range()
            self.plotter.render()
        return super().eventFilter(watched, event)

    def _end_terrain_gesture(self):
        self._terrain_style.EndRotate()
        self._terrain_style.EndPan()

    def reset_camera(self):
        """Fit all visible scene data in the render window."""
        self.plotter.reset_camera()
        self._reset_clipping_range()
        self.plotter.render()

    def _reset_clipping_range(self):
        """Recompute depth clipping from the current rendered scene bounds."""
        self.plotter.renderer.ResetCameraClippingRange()

    def zoom_camera(self, factor):
        """Zoom the current camera, where values below one zoom out."""
        factor = float(factor)
        if factor <= 0:
            raise ValueError("zoom factor must be positive")
        camera = self.plotter.camera
        if camera.GetParallelProjection():
            camera.SetParallelScale(camera.GetParallelScale() / factor)
        else:
            position = np.asarray(camera.GetPosition(), dtype=float)
            focal_point = np.asarray(camera.GetFocalPoint(), dtype=float)
            camera.SetPosition(
                tuple(focal_point + (position - focal_point) / factor)
            )
        self._reset_clipping_range()
        self.plotter.render()

    def _zoom_camera_from_wheel(self, delta):
        if not delta:
            return
        # One wheel step is 120 units. Smaller factors zoom out, larger zoom in.
        steps = delta / 120.0
        self.zoom_camera(1.15 ** steps)

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
            payload = payload.copy(deep=True)
            payload = payload.extract_surface(
                algorithm="dataset_surface",
            ).compute_normals(
                auto_orient_normals=True,
                split_vertices=False,
                inplace=False,
            )
            if block_object is not None and hasattr(block_object, "set_mesh_data"):
                block_object.set_mesh_data(payload)

        if hasattr(payload, "compute_normals") and "Normals" not in payload.point_data:
            payload = payload.compute_normals(
                auto_orient_normals=True,
                split_vertices=False,
                inplace=False,
            )
            if block_object is not None and hasattr(block_object, "set_mesh_data"):
                block_object.set_mesh_data(payload)

        colour_scalars = None
        colourmap = getattr(block_object, "colourmap", None)
        if hasattr(payload, "point_data") and "__colourmap_rgba" in payload.point_data:
            del payload.point_data["__colourmap_rgba"]
        if colourmap is not None and hasattr(payload, "points"):
            points = np.asarray(payload.points)
            elevation = points[:, 2]
            elevation_span = float(elevation.max() - elevation.min()) if len(elevation) else 0.0
            relative_elevation = (
                np.zeros_like(elevation)
                if elevation_span <= 1e-12
                else (elevation - elevation.min()) / elevation_span
            )
            normals = np.asarray(payload.point_data.get("Normals", np.zeros_like(points)))
            normal_z = np.clip((1.0 - normals[:, 2]) * 0.5, 0.0, 1.0)
            field_sources = getattr(
                block_object, "colourmap_field_sources", ("elevation", "normal_z")
            )
            field_values = {
                "elevation": relative_elevation,
                "normal_z": normal_z,
            }
            first_field = field_values.get(field_sources[0], relative_elevation)
            second_field = field_values.get(field_sources[1], normal_z)
            inversions = getattr(
                block_object, "colourmap_field_inversions", (False, False)
            )
            if inversions[0]:
                first_field = 1.0 - first_field
            if inversions[1]:
                second_field = 1.0 - second_field
            colour_scalars = np.clip(
                np.round(colourmap.apply_fields(first_field, second_field) * 255.0),
                0,
                255,
            ).astype(np.uint8)
            payload.point_data["__colourmap_rgba"] = colour_scalars

        name = getattr(object_base, "name", None)
        if hasattr(payload, "GetMapper"):
            actor = self.plotter.add_actor(payload, reset_camera=False)
        else:
            actor = self.plotter.add_mesh(
                payload,
                name=name,
                scalars="__colourmap_rgba" if colour_scalars is not None else None,
                rgb=colour_scalars is not None,
                reset_camera=False,
            )

        actor.SetVisibility(bool(getattr(object_base, "visible", True)))
        self._actors[object_base] = actor
        self.scene_model.add_object(object_base)
        self.reset_camera()
        return actor

    def refresh_object_colourmap(self, object_base):
        """Rebuild an object's actor after its optional colourmap changes."""
        return self.refresh_object(object_base)

    def add_shape(self, object_base, shape):
        """Render a lightweight shape without adding it to scene objects."""
        from objects.shape import Shape

        if not isinstance(shape, Shape):
            raise TypeError("shape must be a Shape")
        key = (object_base, id(shape))
        self.remove_shape(object_base, shape)
        if shape.kind == "text":
            value, position = shape.data
            actor = self.plotter.add_point_labels(
                [position], [str(value)], **shape.style
            )
        else:
            if shape.kind == "line":
                payload = pv.lines_from_points(shape.data, close=False)
            elif shape.kind == "mesh":
                payload = shape.data
            else:
                raise ValueError(f"Unsupported shape kind: {shape.kind}")
            actor = self.plotter.add_mesh(payload, **shape.style)
        actor.SetVisibility(bool(shape.visible))
        self._shape_actors[key] = actor
        self.plotter.render()
        return actor

    def remove_shape(self, object_base, shape):
        key = (object_base, id(shape))
        actor = self._shape_actors.pop(key, None)
        if actor is None:
            return False
        self.plotter.remove_actor(actor)
        self.plotter.render()
        return True

    def remove_object_shapes(self, object_base):
        for key, actor in tuple(self._shape_actors.items()):
            if key[0] is object_base:
                self._shape_actors.pop(key)
                self.plotter.remove_actor(actor)

    def refresh_object(self, object_base):
        """Rebuild an existing actor from the object's current block data."""
        if object_base not in self._actors:
            return False
        camera_position = self.plotter.camera_position
        actor = self._actors.pop(object_base)
        self.plotter.remove_actor(actor)
        self.add_object(object_base)
        self.plotter.camera_position = camera_position
        self.plotter.render()
        return True

    def remove_object(self, object_base: Any):
        self.remove_object_shapes(object_base)
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

    def set_object_transform(self, object_base: Any, transform):
        actor = self._actors.get(object_base)
        if actor is None:
            return False
        from components.timer import as_vtk_matrix

        actor.SetUserMatrix(as_vtk_matrix(transform))
        self.plotter.render()
        return True

    def clear_scene(self):
        self.plotter.clear()
        if self._show_sky_dome:
            self.sky_dome.remove()
            self.sky_dome.add_to(self.plotter)
        self._restore_lighting()
        self._actors.clear()
        self._shape_actors.clear()
        self.scene_model.clear()
        self.plotter.show_axes()
        self.plotter.render()

