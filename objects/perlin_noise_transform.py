from typing import Optional

from PySide6.QtGui import QIcon

from engine.block_objects import PerlinNoiseTransformBlockObject

from .transform import TransformObject


class PerlinNoiseTransformObject(TransformObject):
    """Project object wrapping a multi-band Perlin transform."""

    def __init__(
        self,
        name: str = "Perlin Noise Transform",
        block_object: Optional[PerlinNoiseTransformBlockObject] = None,
        comments: str = "",
        visible: bool = True,
        icon: Optional[QIcon] = None,
        guid: Optional[str] = None,
        auto_register_root: bool = False,
    ):
        block = block_object or PerlinNoiseTransformBlockObject()
        if not isinstance(block, PerlinNoiseTransformBlockObject):
            raise TypeError(
                "PerlinNoiseTransformObject requires a PerlinNoiseTransformBlockObject"
            )
        super().__init__(
            name=name,
            block_object=block,
            comments=comments,
            visible=visible,
            icon=icon,
            guid=guid,
            auto_register_root=auto_register_root,
        )
