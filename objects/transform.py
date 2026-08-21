from typing import Optional

from PySide6.QtGui import QIcon

from engine.block_objects import TransformBlockObject

from .object_base import ObjectBase
from common.icons import get_icon


class TransformObject(ObjectBase):
    """Project object that owns an engine transform block."""

    def __init__(
        self,
        name: str,
        block_object: TransformBlockObject,
        comments: str = "",
        visible: bool = True,
        icon: Optional[QIcon] = None,
        guid: Optional[str] = None,
        auto_register_root: bool = False,
    ):
        if not isinstance(block_object, TransformBlockObject):
            raise TypeError("TransformObject requires a TransformBlockObject")
        self.transform_block_object = block_object
        self.transform_block_object.comments = comments
        super().__init__(
            name=name,
            visible=visible,
            icon=icon if icon is not None else get_icon("photo_changed_filter"),
            guid=guid,
            auto_register_root=auto_register_root,
        )
        self.transform_block_object.name = name
        self.transform_block_object.guid = self.guid

    @property
    def block_object(self):
        return self.transform_block_object

    def apply(self, values):
        return self.transform_block_object.apply(values)
