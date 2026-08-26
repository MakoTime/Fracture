import numpy as np
from PySide6.QtGui import QIcon

from src.common.icons import get_icon
from src.engine.block_objects import IslandBlockObject

from .object_base import ObjectBase, ViewableMixin


class Island(ViewableMixin, ObjectBase):
    """Scene object representing a positioned source mesh island."""

    def __init__(
        self,
        name: str = "Island",
        block_object: IslandBlockObject | None = None,
        comments: str = "",
        icon: QIcon | None = None,
        guid: str | None = None,
        visible: bool = True,
        auto_register_root: bool = False,
    ):
        block = block_object or IslandBlockObject(name=name, guid=guid)
        if not isinstance(block, IslandBlockObject):
            raise TypeError("Island requires an IslandBlockObject")
        self.island_block_object = block
        self.current_transform = None
        super().__init__(
            name=block.name,
            icon=icon if icon is not None else get_icon("floating_island"),
            visible=visible,
            metadata={"comments": comments},
            guid=block.guid,
            auto_register_root=auto_register_root,
        )

    @property
    def block_object(self):
        return self.island_block_object

    @property
    def mesh_data(self):
        return self.block_object.scene_data

    @property
    def core_offset(self):
        return self.block_object.core_offset

    @property
    def orbit_speed(self):
        return self.block_object.orbit_speed

    @property
    def orbit_normal(self):
        return self.block_object.orbit_normal

    @property
    def orbit_angle(self):
        return self.block_object.orbit_angle

    @property
    def curve_mesh(self):
        return self.block_object.curve_mesh

    def update_at_time(self, current_time, delta_seconds=0.0):
        del delta_seconds
        self.current_transform = self.block_object.orbit_transform_at_time(current_time)
        return self.current_transform

    def register_shapes(self, shape_interface):
        if self.block_object.world_config is None or shape_interface.shapes:
            return
        from src.engine.block_tasks.island import _orbit_frame

        centre = np.asarray(self.block_object.world_config.centre, dtype=float)
        angles = np.linspace(0.0, 360.0, 96)
        points = []
        for angle in angles:
            radial, _, _ = _orbit_frame(np.asarray(self.orbit_normal), angle)
            points.append(centre + self.core_offset * radial)
        self.orbit_shape = shape_interface.add_line(
            points,
            name="Orbit",
            color="#8fd3c7",
            line_width=2,
        )
