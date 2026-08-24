from typing import Any

from PySide6.QtGui import QIcon

from common.icons import get_icon
from engine.block_objects import MeshBlockObject

from .object_base import ObjectBase, ViewableMixin

Vector3 = tuple[float, float, float]


class MeshObject(ViewableMixin, ObjectBase):
    """Application object representing an imported mesh dataset."""

    def __init__(
        self,
        name: str,
        mesh_data: Any = None,
        block_object: MeshBlockObject | None = None,
        source_path: str = "",
        comments: str = "",
        scale: Vector3 = (1.0, 1.0, 1.0),
        rotation: Vector3 = (0.0, 0.0, 0.0),
        offset: Vector3 = (0.0, 0.0, 0.0),
        visible: bool = False,
        icon: QIcon | None = None,
        guid: str | None = None,
        auto_register_root: bool = False,
    ):
        self.source_path = source_path
        self.scale = scale
        self.rotation = rotation
        self.offset = offset
        self.mesh_block_object = block_object or MeshBlockObject(mesh_data)
        self.mesh_block_object.name = name
        self.mesh_block_object.guid = guid or self.mesh_block_object.guid
        self.mesh_block_object.comments = comments

        super().__init__(
            name=name,
            icon=icon if icon is not None else get_icon("shape_cube"),
            visible=visible,
            metadata={
                "guid": self.mesh_block_object.guid,
                "comments": self.mesh_block_object.comments,
                "source_path": source_path,
                "scale": scale,
                "rotation": rotation,
                "offset": offset,
            },
            guid=self.mesh_block_object.guid,
            auto_register_root=auto_register_root,
        )

    @property
    def mesh_data(self) -> Any:
        """Return the dataset, loading its serialized payload on demand."""
        return self.mesh_block_object.scene_data

    @property
    def name(self):
        return (
            self.mesh_block_object.name
            if hasattr(self, "mesh_block_object")
            else self._name
        )

    @name.setter
    def name(self, value):
        self._name = value
        if hasattr(self, "mesh_block_object"):
            self.mesh_block_object.name = value

    @property
    def guid(self):
        return (
            self.mesh_block_object.guid
            if hasattr(self, "mesh_block_object")
            else self._guid
        )

    @guid.setter
    def guid(self, value):
        self._guid = value
        if hasattr(self, "mesh_block_object"):
            self.mesh_block_object.guid = value

    @property
    def comments(self):
        return (
            self.mesh_block_object.comments
            if hasattr(self, "mesh_block_object")
            else self._comments
        )

    @comments.setter
    def comments(self, value):
        self._comments = value
        if hasattr(self, "mesh_block_object"):
            self.mesh_block_object.comments = value

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = bool(value)

    @property
    def scene_data(self):
        return (
            self.mesh_block_object.scene_data
            if hasattr(self, "mesh_block_object")
            else self._scene_data
        )

    @scene_data.setter
    def scene_data(self, value):
        self._scene_data = value

    @property
    def block_object(self) -> MeshBlockObject:
        """Backward-compatible alias for the mesh block object."""
        return self.mesh_block_object

    @property
    def colourmap(self):
        return self.mesh_block_object.colourmap

    def set_colourmap(self, colourmap):
        return self.mesh_block_object.set_colourmap(
            getattr(colourmap, "block_object", colourmap),
        )

    @property
    def colourmap_field_sources(self):
        return self.mesh_block_object.colourmap_field_sources

    def set_colourmap_field_sources(self, field1_source, field2_source):
        return self.mesh_block_object.set_colourmap_field_sources(
            field1_source, field2_source
        )

    @property
    def colourmap_field_inversions(self):
        return self.mesh_block_object.colourmap_field_inversions

    def set_colourmap_data_options(self, invert_field1, invert_field2):
        return self.mesh_block_object.set_colourmap_data_options(
            invert_field1, invert_field2
        )

    def set_colourmap_scope(self, scope):
        return self.mesh_block_object.set_colourmap_scope(scope)
