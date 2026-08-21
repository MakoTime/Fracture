from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from .transform import TransformBlockObject


@dataclass
class PerlinNoiseTransformBlockObject(TransformBlockObject):
    """Apply one or more seeded Perlin frequency bands to a scalar field."""

    frequencies: tuple[int, ...] = (4,)
    amplitudes: tuple[float, ...] = (1.0,)
    seed: int = 0
    curve_mode: str = "discrete"
    curve_points: tuple[tuple[float, float], ...] = ()
    curve_handles: tuple = ()
    frequency_start: float = 1.0
    frequency_end: float = 16.0
    sample_count: int = 4
    manual_sampling: bool = False
    preset: str = "Manual"
    preset_options: dict = field(default_factory=dict)

    __hash__ = TransformBlockObject.__hash__

    def __post_init__(self):
        super().__post_init__()
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
        self.manual_sampling = bool(self.manual_sampling)
        self.preset_options = dict(self.preset_options)
        if len(self.frequencies) != len(self.amplitudes):
            raise ValueError("frequencies and amplitudes must have equal lengths")
        if not self.frequencies or any(value < 1 for value in self.frequencies):
            raise ValueError("frequencies must contain positive integers")
        if any(value < 0.0 for value in self.amplitudes):
            raise ValueError("amplitudes must be non-negative")

    def prepare(self):
        if not self.frequencies or len(self.frequencies) != len(self.amplitudes):
            raise ValueError("frequencies and amplitudes must have equal lengths")
        if any(value < 1 for value in self.frequencies):
            raise ValueError("frequencies must contain positive integers")
        if any(value < 0.0 for value in self.amplitudes):
            raise ValueError("amplitudes must be non-negative")
        if self.curve_mode not in ("discrete", "bezier"):
            raise ValueError("curve_mode must be discrete or bezier")
        if self.frequency_start >= self.frequency_end:
            raise ValueError("frequency_start must be below frequency_end")
        return self

    def update_configuration(self, **values):
        allowed = {
            "frequencies",
            "amplitudes",
            "seed",
            "curve_mode",
            "curve_points",
            "curve_handles",
            "frequency_start",
            "frequency_end",
            "sample_count",
            "manual_sampling",
            "preset",
            "preset_options",
        }
        unknown = set(values) - allowed
        if unknown:
            raise TypeError(f"Unknown transform settings: {sorted(unknown)}")
        for name, value in values.items():
            setattr(self, name, value)
        self.frequencies = tuple(int(value) for value in self.frequencies)
        self.amplitudes = tuple(float(value) for value in self.amplitudes)
        self.prepare()
        self.process()
        self.mark_changed()
        return self

    def apply(self, values):
        self.process()
        field = np.asarray(values, dtype=float)
        if field.ndim != 3:
            raise ValueError("Perlin transforms require a three-dimensional field")
        result = field.copy()
        total_amplitude = sum(self.amplitudes)
        if total_amplitude == 0.0:
            return result
        for index, (frequency, amplitude) in enumerate(
            zip(self.frequencies, self.amplitudes)
        ):
            noise = self._build_perlin_noise(
                field.shape,
                frequency,
                self.seed + index,
            )
            result += (noise - 0.5) * amplitude
        return result

    def serialise(self, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "guid": self.guid,
                    "comments": self.comments,
                    "frequencies": list(self.frequencies),
                    "amplitudes": list(self.amplitudes),
                    "seed": self.seed,
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
                    "preset_options": self.preset_options,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return output

    save = serialise

    def serialise_to_directory(self, directory):
        return self.serialise(Path(directory) / f"{self.guid}.perlin_noise_transform.json")

    def noise_field(self, dimensions):
        """Build a normalized field from this transform's frequency bands."""
        self.process()
        dimensions = tuple(max(1, int(value)) for value in dimensions)
        total_amplitude = sum(self.amplitudes)
        if total_amplitude == 0.0:
            return np.full(dimensions, 0.5, dtype=float)
        field = np.zeros(dimensions, dtype=float)
        for index, (frequency, amplitude) in enumerate(
            zip(self.frequencies, self.amplitudes)
        ):
            field += self._build_perlin_noise(
                dimensions,
                frequency,
                self.seed + index,
            ) * amplitude
        return field / total_amplitude

    @staticmethod
    def _build_perlin_noise(dimensions, size, seed):
        dimensions = tuple(max(1, int(value)) for value in dimensions)
        size = max(1, int(size))
        largest_dimension = max(dimensions)
        cells = tuple(
            max(1, round(size * dimension / largest_dimension))
            for dimension in dimensions
        )
        coordinates = np.indices(dimensions, dtype=float)
        fractions = []
        cell_indices = []
        for coordinate, dimension, cell_count in zip(
            coordinates,
            dimensions,
            cells,
        ):
            sample = (coordinate + 0.5) / dimension * cell_count
            index = np.minimum(np.floor(sample).astype(int), cell_count - 1)
            cell_indices.append(index)
            fractions.append(sample - index)

        rng = np.random.default_rng(int(seed))
        gradients = rng.normal(size=tuple(cell + 1 for cell in cells) + (3,))
        gradients /= np.linalg.norm(gradients, axis=-1, keepdims=True)

        def dot_gradient(offsets):
            gradient = gradients[
                tuple(index + offset for index, offset in zip(cell_indices, offsets))
            ]
            distance = np.stack(
                [fraction - offset for fraction, offset in zip(fractions, offsets)],
                axis=-1,
            )
            return np.sum(gradient * distance, axis=-1)

        def fade(values):
            return values * values * values * (values * (values * 6 - 15) + 10)

        corners = {
            offsets: dot_gradient(offsets)
            for offsets in (
                (x, y, z)
                for x in (0, 1)
                for y in (0, 1)
                for z in (0, 1)
            )
        }
        x_amount, y_amount, z_amount = (fade(fraction) for fraction in fractions)
        x_layers = {}
        for y_offset in (0, 1):
            for z_offset in (0, 1):
                x_layers[y_offset, z_offset] = corners[0, y_offset, z_offset] + x_amount * (
                    corners[1, y_offset, z_offset] - corners[0, y_offset, z_offset]
                )
        y_layers = {}
        for z_offset in (0, 1):
            y_layers[z_offset] = x_layers[0, z_offset] + y_amount * (
                x_layers[1, z_offset] - x_layers[0, z_offset]
            )
        result = y_layers[0] + z_amount * (y_layers[1] - y_layers[0])
        result -= result.min()
        maximum = result.max()
        return result / maximum if maximum > 0 else result
