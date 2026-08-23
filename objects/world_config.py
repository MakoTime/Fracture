from typing import Optional

from PySide6.QtGui import QIcon

from common.icons import get_icon
from engine.block_objects import WorldConfigBlockObject

from .object_base import ObjectBase


class WorldConfig(ObjectBase):
    """The singleton project object containing world configuration."""

    def __init__(
        self,
        name: str = "World Config",
        block_object: Optional[WorldConfigBlockObject] = None,
        icon: Optional[QIcon] = None,
        guid: Optional[str] = None,
        auto_register_root: bool = False,
    ):
        block = block_object or WorldConfigBlockObject(name=name, guid=guid)
        if not isinstance(block, WorldConfigBlockObject):
            raise TypeError("WorldConfig requires a WorldConfigBlockObject")
        self.world_config_block_object = block
        super().__init__(
            name=block.name,
            icon=icon if icon is not None else get_icon("earth"),
            guid=block.guid,
            auto_register_root=auto_register_root,
        )

    @property
    def block_object(self):
        return self.world_config_block_object

    @property
    def name(self):
        return self.world_config_block_object.name if hasattr(self, "world_config_block_object") else self._name

    @name.setter
    def name(self, value):
        self._name = value
        if hasattr(self, "world_config_block_object"):
            self.world_config_block_object.name = value

    @property
    def centre(self):
        return self.world_config_block_object.centre

    def update_configuration(self, *, name=None, centre=None):
        result = self.block_object.update_configuration(name=name, centre=centre)
        self.node.name = self.name
        if hasattr(self, "row_data"):
            self.row_data.name = self.name
        return result