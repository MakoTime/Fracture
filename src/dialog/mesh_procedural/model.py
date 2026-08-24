from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np

from src.dialog.base.editor.model import EditorModel
from src.dialog.perlin_noise_transform.model import PerlinNoiseTransformModel
from src.engine.block_tasks import ProceduralMeshTask
from src.objects.procedural_mesh import ProceduralMeshObject


@dataclass
class DropoffDimensionData:
    """Represents a single dimension of a drop-off curve with its points and handles."""

    curve_points: tuple[tuple[float, float], ...] = ()
    curve_handles: tuple[tuple[float, float] | None, ...] = ()
    max: float = 1.0
    amplitudes: tuple[float, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict) -> "DropoffDimensionData":
        """Create a DropoffDimensionData instance from a dictionary."""
        return cls(
            curve_points=tuple(tuple(point) for point in data.get("curve_points", ())),
            curve_handles=tuple(
                tuple(handle) if handle is not None else None
                for handle in data.get("curve_handles", ())
            ),
            max=float(data.get("max", 1.0)),
            amplitudes=tuple(float(a) for a in data.get("amplitudes", ())),
        )

    def to_dict(self) -> dict:
        """Convert the DropoffDimensionData instance to a dictionary."""
        return {
            "curve_points": [list(point) for point in self.curve_points],
            "curve_handles": [
                list(handle) if handle is not None else None
                for handle in self.curve_handles
            ],
            "max": self.max,
            "amplitudes": list(self.amplitudes),
        }


@dataclass
class DropoffData:
    """Represents the drop-off data for all three dimensions (x, y, z)."""

    x: DropoffDimensionData = field(default_factory=DropoffDimensionData)
    y: DropoffDimensionData = field(default_factory=DropoffDimensionData)
    z: DropoffDimensionData = field(default_factory=DropoffDimensionData)

    def to_dict(self) -> dict:
        """Convert the DropoffData instance to a dictionary."""
        return {
            "x": self.x.to_dict(),
            "y": self.y.to_dict(),
            "z": self.z.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DropoffData":
        """Create a DropoffData instance from a dictionary."""
        return cls(
            x=DropoffDimensionData.from_dict(data.get("x", {})),
            y=DropoffDimensionData.from_dict(data.get("y", {})),
            z=DropoffDimensionData.from_dict(data.get("z", {})),
        )

    @classmethod
    def from_list(cls, data_list: list[dict]) -> "DropoffData":
        """Create a DropoffData instance from a list of dictionaries."""
        if len(data_list) != 3:
            raise ValueError(
                "Expected a list of three dictionaries for x, y, z dimensions."
            )
        return cls(
            x=DropoffDimensionData.from_dict(data_list[0]),
            y=DropoffDimensionData.from_dict(data_list[1]),
            z=DropoffDimensionData.from_dict(data_list[2]),
        )

    def __iter__(self):
        """Allow iteration over the dimensions in the order of x, y, z."""
        yield self.x
        yield self.y
        yield self.z


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
    dropoff_dimensions: DropoffData = field(default_factory=DropoffData)
    sample_count: int = 32
    source_grid_data: np.ndarray | None = None
    seed: int | None = None

    def __post_init__(self):
        if isinstance(self.dropoff_dimensions, dict):
            self.dropoff_dimensions = DropoffData.from_dict(self.dropoff_dimensions)

    def __setattr__(self, name, value):
        if (
            name == "dropoff_dimensions"
            and value is not None
            and not isinstance(value, list)
        ):
            value = DropoffData.from_list(value)
        super().__setattr__(name, value)

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
                max_amplitude=transform_block.max_amplitude,
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
        if (
            name == "dropoff_dimensions"
            and value is not None
            and not isinstance(value, DropoffData)
        ):
            if isinstance(value, dict):
                value = DropoffData.from_dict(value)
            elif isinstance(value, list):
                value = DropoffData.from_list(value)
        super().__setattr__(name, value)

    def generate(self) -> ProceduralMeshObject:
        """Run the generation block task synchronously."""
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
        dimensions_data = (
            self.dropoff_dimensions.to_dict()
            if self.dropoff_dimensions is not None
            else None
        )
        return {
            "perlin_noise_transform": transform_data,
            "upper_threshold": self.upper_threshold,
            "lower_threshold": self.lower_threshold,
            "seed": self.seed,
            "dropoff_dimensions": dimensions_data,
        }
