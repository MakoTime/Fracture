from dataclasses import dataclass

from objects.mesh_object import MeshObject


Vector3 = tuple[float, float, float]


@dataclass
class MeshEditModel:
    """Editable metadata and transforms for an existing mesh."""

    mesh_object: MeshObject
    name: str
    comments: str
    scale: Vector3
    rotation: Vector3
    offset: Vector3

    @classmethod
    def from_mesh_object(cls, mesh_object: MeshObject):
        return cls(
            mesh_object=mesh_object,
            name=mesh_object.name,
            comments=mesh_object.comments,
            scale=mesh_object.scale,
            rotation=mesh_object.rotation,
            offset=mesh_object.offset,
        )

    def apply(self) -> MeshObject:
        """Apply the edited values without replacing the mesh object."""
        self.mesh_object.name = self.name or "Mesh"
        self.mesh_object.comments = self.comments
        self.mesh_object.scale = self.scale
        self.mesh_object.rotation = self.rotation
        self.mesh_object.offset = self.offset
        self.mesh_object.metadata.update(
            {
                "comments": self.mesh_object.comments,
                "scale": self.mesh_object.scale,
                "rotation": self.mesh_object.rotation,
                "offset": self.mesh_object.offset,
            }
        )
        self.mesh_object.node.name = self.mesh_object.name
        self.mesh_object.row_data.name = self.mesh_object.name
        return self.mesh_object