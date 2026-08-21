from dataclasses import dataclass

from engine.block_objects import MeshBlockObject
from objects.mesh_object import MeshObject

@dataclass
class MeshColourmapModel:
    mesh_object: MeshObject | None = None
    colourmap: object | None = None
    field1_source: str = "elevation"
    field2_source: str = "normal_z"
    invert_field1: bool = False
    invert_field2: bool = False

    SOURCES = (
        ("elevation", "Relative elevation"),
        ("normal_z", "Inverted surface normal Z"),
    )

    @classmethod
    def from_mesh_object(cls, mesh_object):
        selected = mesh_object.colourmap
        return cls(
            mesh_object=mesh_object,
            colourmap=selected,
            field1_source=mesh_object.colourmap_field_sources[0],
            field2_source=mesh_object.colourmap_field_sources[1],
            invert_field1=mesh_object.colourmap_field_inversions[0],
            invert_field2=mesh_object.colourmap_field_inversions[1],
        )

    def preview_object(self):
        if self.mesh_object is None or self.mesh_object.mesh_data is None:
            return None
        block = MeshBlockObject(
            mesh_data=self.mesh_object.mesh_data.copy(deep=True),
            name=self.mesh_object.name,
            comments=self.mesh_object.comments,
        )
        block.set_colourmap(
            getattr(self.colourmap, "block_object", self.colourmap)
        )
        block.set_colourmap_field_sources(
            self.field1_source,
            self.field2_source,
        )
        block.set_colourmap_data_options(
            self.invert_field1,
            self.invert_field2,
        )
        return MeshObject(
            name=self.mesh_object.name,
            block_object=block,
            visible=True,
            auto_register_root=False,
        )

    def apply(self, mesh_object):
        mesh_object.set_colourmap(self.colourmap)
        mesh_object.set_colourmap_field_sources(
            self.field1_source,
            self.field2_source,
        )
        mesh_object.set_colourmap_data_options(
            self.invert_field1,
            self.invert_field2,
        )
        return mesh_object
