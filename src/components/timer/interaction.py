from collections import OrderedDict

import numpy as np
import vtk


class TimerInterface:
    """Runtime timer representation for one application object."""

    def __init__(self, object_base):
        self.object_base = object_base

    def update(self, elapsed_seconds, delta_seconds):
        update = getattr(self.object_base, "update_at_time", None)
        if not callable(update):
            return None
        return update(elapsed_seconds, delta_seconds)


class TimerController:
    """Dispatch simulation time to registered object representations."""

    def __init__(self, scene_viewer=None):
        self.scene_viewer = scene_viewer
        self.elapsed_seconds = 0.0
        self._interfaces = OrderedDict()

    def attach(self, object_base):
        interface = TimerInterface(object_base)
        self._interfaces[object_base] = interface
        object_base.timer_controller = self
        object_base.timer_interface = interface
        return interface

    def detach(self, object_base):
        interface = self._interfaces.pop(object_base, None)
        if interface is None:
            return False
        if getattr(object_base, "timer_interface", None) is interface:
            del object_base.timer_interface
        if getattr(object_base, "timer_controller", None) is self:
            del object_base.timer_controller
        return True

    def clear(self):
        for object_base in tuple(self._interfaces):
            self.detach(object_base)
        self.elapsed_seconds = 0.0

    def advance(self, delta_seconds):
        delta_seconds = float(delta_seconds)
        self.elapsed_seconds += delta_seconds
        for interface in tuple(self._interfaces.values()):
            transform = interface.update(self.elapsed_seconds, delta_seconds)
            if transform is not None and self.scene_viewer is not None:
                self.scene_viewer.set_object_transform(
                    interface.object_base,
                    transform,
                )
        return self.elapsed_seconds


def as_vtk_matrix(transform):
    """Convert a 4x4 numeric transform to a VTK matrix."""
    values = np.asarray(transform, dtype=float)
    if values.shape != (4, 4) or not np.isfinite(values).all():
        raise ValueError("transform must be a finite 4x4 matrix")
    matrix = vtk.vtkMatrix4x4()
    for row in range(4):
        for column in range(4):
            matrix.SetElement(row, column, float(values[row, column]))
    return matrix
