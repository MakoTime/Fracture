from typing import Any, Optional

from PySide6.QtGui import QIcon

from common.icons import get_icon
from .object_base import ObjectBase


Vector3 = tuple[float, float, float]


class MeshObject(ObjectBase):
    """Application object representing an imported mesh dataset."""

    def __init__(
        self,
        name: str,
        mesh_data: Any,
        source_path: str = "",
        comments: str = "",
        scale: Vector3 = (1.0, 1.0, 1.0),
        rotation: Vector3 = (0.0, 0.0, 0.0),
        offset: Vector3 = (0.0, 0.0, 0.0),
        visible: bool = False,
        icon: Optional[QIcon] = None,
        guid: Optional[str] = None,
        auto_register_root: bool = False,
    ):
        self.source_path = source_path
        self.comments = comments
        self.scale = scale
        self.rotation = rotation
        self.offset = offset

        super().__init__(
            name=name,
            icon=icon if icon is not None else get_icon("grid"),
            visible=visible,
            scene_data=mesh_data,
            metadata={
                "guid": guid,
                "comments": comments,
                "source_path": source_path,
                "scale": scale,
                "rotation": rotation,
                "offset": offset,
            },
            guid=guid,
            auto_register_root=auto_register_root,
        )
