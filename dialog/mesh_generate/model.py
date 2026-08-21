from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np
from objects.generated_mesh import GeneratedMesh
from engine.block_tasks import MeshGenerateTask
from dialog.perlin_noise_transform import PerlinNoiseTransformModel


@dataclass
class MeshGenerateModel:
    """Editable settings for a basic generated mesh."""

    name: str = "Generated Mesh"
    grid_size: tuple[int, int, int] = (10, 10, 10)
    show_grid: bool = False
    show_mask_surface: bool = True
    flexible_masks: bool = False
    flexible_grid: bool = True
    noise_enabled: bool = False
    noise_minimum: float = 0.25
    noise_maximum: float = 0.75
    noise_penetration: int = 1
    perlin_noise_transform: PerlinNoiseTransformModel | None = None
    source_grid_data: np.ndarray | None = None
    x_mask: np.ndarray | None = None
    y_mask: np.ndarray | None = None
    z_mask: np.ndarray | None = None
    guid: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def from_generated_mesh(cls, mesh_object):
        settings = dict(mesh_object.metadata.get("generation_settings", {}))
        for legacy_key in ("noise_amplitude", "noise_size", "noise_seed"):
            settings.pop(legacy_key, None)
        block = mesh_object.mesh_block_object
        settings["noise_enabled"] = bool(
            getattr(block, "noise_enabled", settings.get("noise_enabled", False))
        )
        if getattr(block, "perlin_noise_transform", None) is None:
            settings["perlin_noise_transform"] = None
        settings["name"] = mesh_object.name
        settings["grid_size"] = tuple(mesh_object.grid_shape)
        settings["guid"] = mesh_object.guid
        settings["show_grid"] = mesh_object.visible
        if "generation_settings" not in mesh_object.metadata:
            settings["source_grid_data"] = mesh_object.grid_data.copy()
        for axis in "xyz":
            mask = settings.get(f"{axis}_mask")
            if mask is not None:
                settings[f"{axis}_mask"] = np.asarray(mask, dtype=bool)
        transform_data = settings.get("perlin_noise_transform")
        if isinstance(transform_data, dict):
            settings["perlin_noise_transform"] = PerlinNoiseTransformModel.from_json(
                transform_data
            )
        return cls(**settings)

    def generate(self) -> GeneratedMesh:
        """Synchronously run the generation block task."""
        task = self.to_mesh_generate_task()
        prepared = task.prepare()
        block_object = task.execute(prepared)
        generated = GeneratedMesh(
            name=self.name.strip() or "Generated Mesh",
            block_object=block_object,
            grid_data=task.grid_data,
            guid=self.guid,
            auto_register_root=False,
        )
        generated.metadata["generation_settings"] = self._settings()
        return generated

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
            "flexible_grid": self.flexible_grid,
            "show_mask_surface": self.show_mask_surface,
            "flexible_masks": self.flexible_masks,
            "noise_enabled": self.noise_enabled,
            "noise_minimum": self.noise_minimum,
            "noise_maximum": self.noise_maximum,
            "noise_penetration": self.noise_penetration,
            "perlin_noise_transform": transform_data,
            "x_mask": None if self.x_mask is None else self.x_mask.copy(),
            "y_mask": None if self.y_mask is None else self.y_mask.copy(),
            "z_mask": None if self.z_mask is None else self.z_mask.copy(),
        }

    def to_mesh_generate_task(self) -> MeshGenerateTask:
        """Create the engine task for this generation configuration."""
        return MeshGenerateTask(self)

    def mask_shape(self, axis: str) -> tuple[int, int]:
        dimensions = tuple(max(1, int(value)) for value in self.grid_size)
        shapes = {
            "x": (dimensions[1], dimensions[2]),
            "y": (dimensions[0], dimensions[2]),
            "z": (dimensions[0], dimensions[1]),
        }
        try:
            return shapes[axis.lower()]
        except KeyError as error:
            raise ValueError(f"unknown mask axis: {axis}") from error

    def get_mask(self, axis: str):
        return getattr(self, f"{axis.lower()}_mask")

    def set_mask(self, axis: str, mask):
        axis = axis.lower()
        if mask is None:
            setattr(self, f"{axis}_mask", None)
            return
        values = np.asarray(mask, dtype=bool)
        if values.shape != self.mask_shape(axis):
            raise ValueError(
                f"{axis.upper()} mask must have shape {self.mask_shape(axis)}"
            )
        setattr(self, f"{axis}_mask", values.copy())

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
