from typing import Optional

import numpy as np
from PySide6.QtGui import QIcon

from common.icons import get_icon
from engine.block_objects import IslandBlockObject

from .object_base import ObjectBase


class Island(ObjectBase):
    """Scene object representing a positioned source mesh island."""

    def __init__(
        self,
        name: str = "Island",
        block_object: Optional[IslandBlockObject] = None,
        comments: str = "",
        icon: Optional[QIcon] = None,
        guid: Optional[str] = None,
        visible: bool = True,
        auto_register_root: bool = False,
    ):
        block = block_object or IslandBlockObject(name=name, guid=guid)
        if not isinstance(block, IslandBlockObject):
            raise TypeError("Island requires an IslandBlockObject")
        self.island_block_object = block
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

    def update_at_time(self, elapsed_seconds, delta_seconds=0.0):
        del delta_seconds
        return self.block_object.orbit_transform_at_time(elapsed_seconds)

    def register_shapes(self, shape_interface):
        if self.block_object.world_config is None or shape_interface.shapes:
            return
        from engine.block_tasks.island import _orbit_frame

        centre = np.asarray(self.block_object.world_config.centre, dtype=float)
        angles = np.linspace(0.0, 360.0, 96)
        points = []
        for angle in angles:
            radial, _, _ = _orbit_frame(
                np.asarray(self.orbit_normal), angle
            )
            points.append(centre + self.core_offset * radial)
        self.orbit_shape = shape_interface.add_line(
            points,
            name="Orbit",
            color="#8fd3c7",
            line_width=2,
        )