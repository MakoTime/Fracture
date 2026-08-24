from collections import defaultdict

from objects.shape import Shape


class ShapeInterface:
    """Table-facing shape API for one owning scene object."""

    def __init__(self, controller, object_base):
        self.controller = controller
        self.object_base = object_base

    @property
    def shapes(self):
        return self.controller.shapes_for(self.object_base)

    def add_line(self, points, **style):
        return self.controller.add_line(self.object_base, points, **style)

    def add_text(self, value, position, **style):
        return self.controller.add_text(self.object_base, value, position, **style)

    def add_mesh(self, data, **style):
        return self.controller.add_mesh(self.object_base, data, **style)

    def clear(self):
        return self.controller.clear(self.object_base)

    def set_visible(self, shape, visible):
        return self.controller.set_visible(self.object_base, shape, visible)

    def __str__(self):
        return f"Shapes ({len(self.shapes)})"


class ShapeController:
    """Own and render lightweight shapes attached to scene/table objects."""

    def __init__(self, scene_viewer=None, table_model=None):
        self.scene_viewer = scene_viewer
        self.table_model = table_model
        self._shapes = defaultdict(list)

    def attach(self, object_base):
        object_base.shape_controller = self
        object_base.shapes = self._shapes[object_base]
        object_base.shape_interface = ShapeInterface(self, object_base)
        if getattr(object_base, "row_data", None) is not None:
            object_base.row_data.other = object_base.shape_interface
        register_shapes = getattr(object_base, "register_shapes", None)
        if (
            callable(register_shapes)
            and not getattr(object_base, "_registering_shapes", False)
            and not self._shapes[object_base]
        ):
            object_base._registering_shapes = True
            try:
                register_shapes(object_base.shape_interface)
            finally:
                del object_base._registering_shapes
        return self

    def add(self, object_base, shape):
        if not isinstance(shape, Shape):
            raise TypeError("shape must be a Shape")
        self.attach(object_base)
        self._shapes[object_base].append(shape)
        if self.scene_viewer is not None and hasattr(self.scene_viewer, "add_shape"):
            self.scene_viewer.add_shape(object_base, shape)
        self._refresh_table(object_base)
        return shape

    def add_line(self, object_base, points, **style):
        return self.add(object_base, Shape.line(points, **style))

    def add_text(self, object_base, value, position, **style):
        return self.add(object_base, Shape.text(value, position, **style))

    def add_mesh(self, object_base, data, **style):
        return self.add(object_base, Shape.mesh(data, **style))

    def remove(self, object_base, shape):
        shapes = self._shapes.get(object_base, ())
        if shape not in shapes:
            return False
        shapes.remove(shape)
        if self.scene_viewer is not None and hasattr(self.scene_viewer, "remove_shape"):
            self.scene_viewer.remove_shape(object_base, shape)
        self._refresh_table(object_base)
        return True

    def set_visible(self, object_base, shape, visible):
        shapes = self._shapes.get(object_base, ())
        if shape not in shapes:
            return False
        shape.visible = bool(visible)
        if self.scene_viewer is not None and hasattr(
            self.scene_viewer, "set_shape_visibility"
        ):
            self.scene_viewer.set_shape_visibility(object_base, shape, visible)
        self._refresh_table(object_base)
        return True

    def clear(self, object_base):
        for shape in tuple(self._shapes.get(object_base, ())):
            self.remove(object_base, shape)

    def shapes_for(self, object_base):
        return tuple(self._shapes.get(object_base, ()))

    def _refresh_table(self, object_base):
        if self.table_model is not None and hasattr(self.table_model, "refresh_object"):
            self.table_model.refresh_object(object_base)
