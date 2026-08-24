from dataclasses import dataclass
from uuid import uuid4

from src.engine.block_objects import MeshBlockObject
from src.engine.block_tasks import MeshFilterTask
from src.objects.mesh_object import MeshObject


@dataclass
class MeshFilterModel:
    source_mesh: object
    name: str = "Filtered Mesh"
    noise_enabled: bool = False
    noise_minimum: float = 0.25
    noise_maximum: float = 0.75
    perlin_noise_transform: object | None = None

    @classmethod
    def from_mesh(cls, mesh):
        return cls(
            source_mesh=mesh,
            name=f"{mesh.name} Filtered",
            noise_enabled=False,
            perlin_noise_transform=None,
        )

    @property
    def has_transform(self):
        return self.perlin_noise_transform is not None

    @property
    def filter_enabled(self):
        return bool(self.noise_enabled and self.has_transform)

    def _transform_block(self):
        transform = self.perlin_noise_transform
        block = getattr(transform, "block_object", transform)
        if hasattr(block, "to_object"):
            block = block.to_object().block_object
        if not hasattr(block, "noise_field"):
            raise TypeError("filter transform must provide a noise field")
        return block

    def preview_mesh_data(self):
        """Build preview surfaces without creating a persistent mesh object."""
        task = MeshFilterTask(
            self.source_mesh.mesh_block_object,
            self._transform_block(),
            self.noise_minimum,
            self.noise_maximum,
        )
        task.execute(task.prepare())
        return task.mesh_data

    def generate(self):
        source = self.source_mesh
        if not self.filter_enabled:
            raise ValueError("an enabled filter transform is required")
        source_block = source.mesh_block_object
        transform_block = self._transform_block()
        filtered_block = MeshBlockObject(
            name=self.name.strip() or "Filtered Mesh",
            guid=f"{source.guid}-filtered-{uuid4().hex}",
        )
        filtered_block.add_child_block_object(transform_block, dependent=True)
        task = MeshFilterTask(
            source_block,
            transform_block,
            self.noise_minimum,
            self.noise_maximum,
            block_object=filtered_block,
        )
        task.execute(task.prepare())
        filtered_block.add_child_block_object(source_block, dependent=True)
        filtered_block.filter_parameters = {
            "noise_minimum": self.noise_minimum,
            "noise_maximum": self.noise_maximum,
        }
        return MeshObject(
            name=filtered_block.name,
            mesh_data=task.mesh_data,
            block_object=filtered_block,
            visible=True,
            auto_register_root=False,
        )
