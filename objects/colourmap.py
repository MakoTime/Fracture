from typing import Optional

from PySide6.QtGui import QIcon

from components.tree.roots import colourmap_root
from engine.block_objects import ColourmapBlockObject

from .object_base import ObjectBase


class ColourmapObject(ObjectBase):
    """Project object wrapping an engine colourmap block."""

    def __init__(
        self,
        name: str = "Colourmap",
        block_object: Optional[ColourmapBlockObject] = None,
        comments: str = "",
        visible: bool = True,
        icon: Optional[QIcon] = None,
        guid: Optional[str] = None,
        auto_register_root: bool = False,
    ):
        block = block_object or ColourmapBlockObject()
        if not isinstance(block, ColourmapBlockObject):
            raise TypeError(
                "ColourmapObject requires a ColourmapBlockObject"
            )
        self.colourmap_block_object = block
        super().__init__(
            name=name,
            icon=icon,
            visible=visible,
            guid=guid,
            auto_register_root=auto_register_root,
        )
        self.colourmap_block_object.comments = comments
        self.colourmap_block_object.name = name
        self.colourmap_block_object.guid = self.guid

    @property
    def block_object(self):
        return self.colourmap_block_object

    @property
    def stops(self):
        return self.colourmap_block_object.stops

    def apply(self, values):
        return self.colourmap_block_object.apply(values)

    def add_to_tree(self, tree_manager, parent=None):
        return super().add_to_tree(tree_manager, parent or colourmap_root)
