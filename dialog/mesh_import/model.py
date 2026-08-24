from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from application.importers import register_import_binding
from engine.block_objects import MeshBlockObject
from engine.block_tasks import MeshImportTask
from objects.mesh_object import MeshObject

Vector3 = tuple[float, float, float]


@dataclass
class MeshImportModel:
    """Editable metadata and transforms for an imported mesh."""

    source_path: str = ""
    name: str = "Imported Mesh"
    guid: str = field(default_factory=lambda: str(uuid4()))
    comments: str = ""
    scale: Vector3 = (1.0, 1.0, 1.0)
    rotation: Vector3 = (0.0, 0.0, 0.0)
    offset: Vector3 = (0.0, 0.0, 0.0)
    mesh_data: Any | None = None
    add_to_scene: bool = False
    low_threshold: float = 0.0
    high_threshold: float = 255.0
    vertical_scale: float = 1.0

    @staticmethod
    def bind_controller(object_importer, tree_view, parent=None, engine_runner=None):
        """Attach mesh import actions to a project tree and importer."""
        from application.importers import MeshImportController

        return MeshImportController(
            object_importer=object_importer,
            tree_view=tree_view,
            parent=parent,
            engine_runner=engine_runner,
        )

    bind_controller = register_import_binding(bind_controller)

    @property
    def file_name(self) -> str:
        return Path(self.source_path).name if self.source_path else ""

    def to_mesh_import_task(self) -> MeshImportTask:
        """Create the transient operation for this import."""
        return MeshImportTask(self)

    def to_mesh_object(self, block_object=None) -> MeshObject:
        """Create the application mesh object represented by this model."""
        if block_object is None:
            block_object = MeshBlockObject(
                mesh_data=self.mesh_data,
                name=self.name,
                guid=self.guid,
                comments=self.comments,
            )
        return MeshObject(
            name=self.name,
            block_object=block_object,
            source_path=self.source_path,
            comments=self.comments,
            scale=self.scale,
            rotation=self.rotation,
            offset=self.offset,
            guid=self.guid,
            auto_register_root=False,
        )

    def to_object_base(self) -> MeshObject:
        """Backward-compatible alias for creating the imported mesh object."""
        return self.to_mesh_object()
