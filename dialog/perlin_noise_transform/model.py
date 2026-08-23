from dataclasses import dataclass, field
from uuid import uuid4, UUID

from dialog.base.editor import EditorModel

from objects.perlin_noise_transform import PerlinNoiseTransformObject


@dataclass
class PerlinNoiseTransformModel(EditorModel):
    """Editable settings for a multi-band Perlin noise transform."""

    name: str = "Perlin Noise Transform"
    frequencies: tuple[int, ...] = (4,)
    amplitudes: tuple[float, ...] = (1.0,)
    guid: str = field(default_factory=lambda: str(uuid4()))
    seed: int | None = None
    curve_mode: str = "bezier"
    curve_points: tuple[tuple[float, float], ...] = ()
    curve_handles: tuple = ()
    frequency_start: float = 1.0
    frequency_end: float = 8.0
    sample_count: int = 4
    manual_sampling: bool = False
    preset: str = "Manual"
    preset_options: dict = field(default_factory=dict)
    application_mode: str = "voxel_remesh"
    penetration: int = 1

    def __post_init__(self):
        if self.seed is None:
            self.seed = UUID(self.guid).int & 0x7FFFFFFF
        self.frequencies = tuple(int(value) for value in self.frequencies)
        self.amplitudes = tuple(float(value) for value in self.amplitudes)
        self.curve_points = tuple(
            (float(point[0]), float(point[1])) for point in self.curve_points
        )
        self.curve_handles = tuple(
            None
            if handles is None
            else tuple((float(point[0]), float(point[1])) for point in handles)
            for handles in self.curve_handles
        )
        self.sample_count = max(1, int(self.sample_count))
        self.manual_sampling = bool(self.manual_sampling)
        self.penetration = max(1, int(self.penetration))
        self._validate()

    def _validate(self):
        if not self.frequencies or len(self.frequencies) != len(self.amplitudes):
            raise ValueError("frequencies and amplitudes must have equal lengths")
        if any(value < 1 for value in self.frequencies):
            raise ValueError("frequencies must be positive integers")
        if any(value < 0.0 for value in self.amplitudes):
            raise ValueError("amplitudes must be non-negative")
        if self.curve_mode not in ("discrete", "bezier"):
            raise ValueError("curve_mode must be discrete or bezier")
        if self.frequency_start >= self.frequency_end:
            raise ValueError("frequency_start must be below frequency_end")
        if self.application_mode not in (
            "surface_displacement",
            "voxel_remesh",
            "noise_mask",
        ):
            raise ValueError("application_mode is not supported")

    def to_object(self):
        from engine.block_objects import PerlinNoiseTransformBlockObject

        block = PerlinNoiseTransformBlockObject(
            frequencies=self.frequencies,
            amplitudes=self.amplitudes,
            seed=self.seed,
            guid=self.guid,
            curve_mode=self.curve_mode,
            curve_points=self.curve_points,
            curve_handles=self.curve_handles,
            frequency_start=self.frequency_start,
            frequency_end=self.frequency_end,
            sample_count=self.sample_count,
            manual_sampling=self.manual_sampling,
            preset=self.preset,
            preset_options=self.preset_options,
            application_mode=self.application_mode,
            penetration=self.penetration,
        )
        return PerlinNoiseTransformObject(
            name=self.name.strip() or "Perlin Noise Transform",
            block_object=block,
            guid=self.guid,
            auto_register_root=False,
        )

    @classmethod
    def from_json(cls, data):
        return cls(
            name=data.get("name", cls.name),
            frequencies=tuple(data.get("frequencies", (4,))),
            amplitudes=tuple(data.get("amplitudes", (1.0,))),
            seed=int(data.get("seed", 0)),
            guid=data.get("guid", str(uuid4())),
            curve_mode=data.get("curve_mode", "bezier"),
            curve_points=tuple(data.get("curve_points", ())),
            curve_handles=tuple(data.get("curve_handles", ())),
            frequency_start=float(data.get("frequency_start", 1.0)),
            frequency_end=float(data.get("frequency_end", 8.0)),
            sample_count=int(data.get("sample_count", len(data.get("frequencies", (4,))))),
            manual_sampling=bool(data.get("manual_sampling", False)),
            preset=data.get("preset", "Manual"),
            preset_options=dict(data.get("preset_options", {})),
            application_mode=data.get("application_mode", "voxel_remesh"),
            penetration=int(data.get("penetration", 1)),
        )

    def to_json(self):
        return {
            "type": "perlin_noise_transform",
            "name": self.name,
            "frequencies": list(self.frequencies),
            "amplitudes": list(self.amplitudes),
            "seed": self.seed,
            "guid": self.guid,
            "curve_mode": self.curve_mode,
            "curve_points": [list(point) for point in self.curve_points],
            "curve_handles": [
                None if handles is None else [list(point) for point in handles]
                for handles in self.curve_handles
            ],
            "frequency_start": self.frequency_start,
            "frequency_end": self.frequency_end,
            "sample_count": self.sample_count,
            "manual_sampling": self.manual_sampling,
            "preset": self.preset,
            "preset_options": dict(self.preset_options),
            "application_mode": self.application_mode,
            "penetration": self.penetration,
        }
