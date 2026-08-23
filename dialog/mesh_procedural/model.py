
from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np

from dialog.base.editor.model import EditorModel
from dialog.perlin_noise_transform.model import PerlinNoiseTransformModel
from engine.block_tasks import ProceduralMeshTask
from objects.procedural_mesh import ProceduralMeshObject


@dataclass
class MeshProceduralModel(EditorModel):
    """Editable settings for a procedural mesh."""

    name: str = "Procedural Mesh"
    grid_size: tuple[int, int, int] = (10, 10, 10)
    show_grid: bool = True
    perlin_noise_transform: PerlinNoiseTransformModel | None = None
    guid: str = field(default_factory=lambda: str(uuid4()))
    upper_threshold: float = 1.0
    lower_threshold: float = 0.0
    source_grid_data: np.ndarray | None = None
    seed: int | None = None

    @classmethod
    def from_procedural_mesh(cls, mesh_object):
        settings = dict(mesh_object.metadata.get("procedural_settings", {}))
        settings.pop("node_minimum", None)
        settings.pop("node_maximum", None)
        block = mesh_object.mesh_block_object
        transform = block.perlin_noise_transform
        transform_model = None
        if transform is not None:
            transform_block = getattr(transform, "block_object", transform)
            transform_model = PerlinNoiseTransformModel(
                name=transform.name,
                frequencies=transform_block.frequencies,
                amplitudes=transform_block.amplitudes,
                seed=transform_block.seed,
                guid=transform_block.guid,
                curve_mode=transform_block.curve_mode,
                curve_points=transform_block.curve_points,
                curve_handles=transform_block.curve_handles,
                frequency_start=transform_block.frequency_start,
                frequency_end=transform_block.frequency_end,
                sample_count=transform_block.sample_count,
                manual_sampling=transform_block.manual_sampling,
                preset=transform_block.preset,
                preset_options=transform_block.preset_options,
                application_mode=transform_block.application_mode,
                penetration=transform_block.penetration,
            )
        settings["name"] = mesh_object.name
        settings["guid"] = mesh_object.guid
        settings["grid_size"] = tuple(mesh_object.grid_shape)
        settings["show_grid"] = mesh_object.visible
        settings["perlin_noise_transform"] = transform_model
        settings["seed"] = transform_model.seed if transform_model is not None else None
        return cls(**settings)
    
    def __setattr__(self, name, value):
        if name == "perlin_noise_transform" and value is not None:
            transform = getattr(value, "block_object", value)
            self.seed = transform.seed
        super().__setattr__(name, value)
    
    def generate(self) -> ProceduralMeshObject:
        """Synchronously run the generation block task."""
        task = self.to_mesh_generate_task()
        prepared = task.prepare()
        block_object = task.execute(prepared)
        procedural = ProceduralMeshObject(
            name=self.name.strip() or "Procedural Mesh",
            block_object=block_object,
            grid_data=task.grid_data,
            guid=self.guid,
            auto_register_root=False,
        )
        procedural.metadata["procedural_settings"] = self._settings()
        return procedural

    def to_mesh_generate_task(self) -> ProceduralMeshTask:
        """Create the engine task for this procedural mesh configuration."""
        return ProceduralMeshTask(self)
    
    def grid_points(self):
        """Return preview points for the configured integer grid dimensions."""
        dimensions = tuple(max(1, int(value)) for value in self.grid_size)
        x, y, z = np.meshgrid(
            np.arange(dimensions[0]),
            np.arange(dimensions[1]),
            np.arange(dimensions[2]),
            indexing="ij",
        )
        return np.column_stack((x.ravel(), y.ravel(), z.ravel()))
    
    def _settings(self):
        transform = self.perlin_noise_transform
        if hasattr(transform, "block_object"):
            transform = transform.block_object
        if hasattr(transform, "to_json"):
            transform_data = transform.to_json()
        elif transform is None:
            transform_data = None
        else:
            transform_data = {
                "type": "perlin_noise_transform",
                "name": transform.name,
                "frequencies": list(transform.frequencies),
                "amplitudes": list(transform.amplitudes),
                "seed": transform.seed,
                "guid": transform.guid,
            }
        return {
            "perlin_noise_transform": transform_data,
            "upper_threshold": self.upper_threshold,
            "lower_threshold": self.lower_threshold,
            "seed": self.seed,
        }