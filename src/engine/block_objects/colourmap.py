import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType

import numpy as np

from .base_block_object import BlockObject
from .perlin_noise import PerlinNoiseTransformBlockObject


@dataclass
class ColourmapBlockObject(BlockObject):
    """Engine-owned linear colourmap defined by normalized RGBA stops."""

    stops: tuple[tuple[float, tuple[float, float, float, float]], ...] = field(
        default_factory=lambda: (
            (0.0, (0.0, 0.0, 0.0, 1.0)),
            (1.0, (1.0, 1.0, 1.0, 1.0)),
        )
    )
    name: str = "Colourmap"
    field1_name: str = "Field 1"
    field2_name: str = "Field 2"
    field1_positions: tuple[float, ...] = (0.0, 1.0)
    field2_positions: tuple[float, ...] = (0.0, 1.0)
    colour_grid: tuple = ()
    field1_curve_points: tuple = ((0.0, 0.0), (1.0, 1.0))
    field1_curve_handles: tuple = (None, None)
    field2_curve_points: tuple = ((0.0, 0.0), (1.0, 1.0))
    field2_curve_handles: tuple = (None, None)
    guid: str | None = None
    comments: str = ""
    perlin_noise_transform: PerlinNoiseTransformBlockObject | None = None
    noise_enabled: bool = True

    __hash__ = BlockObject.__hash__

    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)
        self.stops = self._normalize_stops(self.stops)
        self.field1_name = self.field1_name.strip() or "Field 1"
        self.field2_name = self.field2_name.strip() or "Field 2"
        self.field1_positions = self._normalize_positions(self.field1_positions)
        self.field2_positions = self._normalize_positions(self.field2_positions)
        if not self.colour_grid:
            self.colour_grid = tuple(
                tuple(stop[1] for stop in self.stops) for _ in self.field2_positions
            )
        self.colour_grid = self._normalize_grid(self.colour_grid)
        if len(self.colour_grid) != len(self.field2_positions) or len(
            self.colour_grid[0]
        ) != len(self.field1_positions):
            raise ValueError("Colourmap grid must match both field position lists")
        self.field1_curve_points = self._normalize_curve_points(
            self.field1_curve_points
        )
        self.field1_curve_handles = self._normalize_curve_handles(
            self.field1_curve_handles
        )
        self.field2_curve_points = self._normalize_curve_points(
            self.field2_curve_points
        )
        self.field2_curve_handles = self._normalize_curve_handles(
            self.field2_curve_handles
        )
        if self.perlin_noise_transform is not None and not isinstance(
            self.perlin_noise_transform,
            PerlinNoiseTransformBlockObject,
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        self.noise_enabled = bool(self.noise_enabled)
        if self.perlin_noise_transform is not None:
            self.add_change_child_block_object(self.perlin_noise_transform)
            self.perlin_noise_transform.add_destruction_callback(
                self._on_noise_transform_destroyed
            )

    @staticmethod
    def _normalize_curve_points(points):
        normalized = tuple(
            sorted((float(point[0]), float(point[1])) for point in points)
        )
        if len(normalized) < 2:
            return ((0.0, 0.0), (1.0, 1.0))
        return ((0.0, normalized[0][1]), *normalized[1:-1], (1.0, normalized[-1][1]))

    @staticmethod
    def _normalize_curve_handles(handles):
        return tuple(
            None
            if handle is None
            else tuple((float(point[0]), float(point[1])) for point in handle)
            for handle in handles
        )

    @staticmethod
    def _json_handles(handles):
        return [
            None if handle is None else [list(point) for point in handle]
            for handle in handles
        ]

    @staticmethod
    def _normalize_positions(positions):
        values = tuple(sorted(float(value) for value in positions))
        if len(values) < 2 or values[0] < 0.0 or values[-1] > 1.0:
            raise ValueError("Colourmap field positions must be between 0 and 1")
        if len(set(values)) != len(values):
            raise ValueError("Colourmap field positions must be unique")
        return values

    @staticmethod
    def _normalize_grid(grid):
        if len(grid) < 2 or any(len(row) < 2 for row in grid):
            raise ValueError("Colourmap grids require at least two rows and columns")
        normalized = []
        for row in grid:
            normalized_row = []
            for colour in row:
                rgba = tuple(float(channel) for channel in colour)
                if len(rgba) == 3:
                    rgba += (1.0,)
                if len(rgba) != 4 or any(
                    channel < 0.0 or channel > 1.0 for channel in rgba
                ):
                    raise ValueError("Colourmap channels must be between 0 and 1")
                normalized_row.append(rgba)
            normalized.append(tuple(normalized_row))
        if any(len(row) != len(normalized[0]) for row in normalized):
            raise ValueError("Colourmap grid rows must have equal lengths")
        return tuple(normalized)

    @staticmethod
    def _normalize_stops(stops: Iterable):
        normalized = []
        for position, colour in stops:
            rgba = tuple(float(channel) for channel in colour)
            if len(rgba) == 3:
                rgba += (1.0,)
            if len(rgba) != 4:
                raise ValueError("Colourmap colours must be RGB or RGBA")
            normalized.append((float(position), rgba))
        normalized.sort(key=lambda stop: stop[0])
        if len(normalized) < 2:
            raise ValueError("Colourmaps require at least two stops")
        if normalized[0][0] < 0.0 or normalized[-1][0] > 1.0:
            raise ValueError("Colourmap stop positions must be between 0 and 1")
        if any(
            position == next_position
            for (position, _), (next_position, _) in pairwise(normalized)
        ):
            raise ValueError("Colourmap stop positions must be unique")
        if any(
            channel < 0.0 or channel > 1.0
            for _, colour in normalized
            for channel in colour
        ):
            raise ValueError("Colourmap channels must be between 0 and 1")
        return tuple(normalized)

    def prepare(self):
        stops = self._normalize_stops(self.stops)
        field1_positions = self._normalize_positions(self.field1_positions)
        field2_positions = self._normalize_positions(self.field2_positions)
        colour_grid = self._normalize_grid(self.colour_grid)
        field1_curve_points = self._normalize_curve_points(self.field1_curve_points)
        field1_curve_handles = self._normalize_curve_handles(self.field1_curve_handles)
        field2_curve_points = self._normalize_curve_points(self.field2_curve_points)
        field2_curve_handles = self._normalize_curve_handles(self.field2_curve_handles)
        if len(colour_grid) != len(field2_positions) or len(colour_grid[0]) != len(
            field1_positions
        ):
            raise ValueError("Colourmap grid must match both field position lists")
        if self.perlin_noise_transform is not None and not isinstance(
            self.perlin_noise_transform,
            PerlinNoiseTransformBlockObject,
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        return MappingProxyType(
            {
                "stops": stops,
                "field1_positions": field1_positions,
                "field2_positions": field2_positions,
                "colour_grid": colour_grid,
                "field1_curve_points": field1_curve_points,
                "field1_curve_handles": field1_curve_handles,
                "field2_curve_points": field2_curve_points,
                "field2_curve_handles": field2_curve_handles,
                "noise_enabled": bool(self.noise_enabled),
            }
        )

    def process(self, prepared, progress_callback=None):
        if progress_callback:
            progress_callback(1.0)
        self.validate()
        return self

    def calculate_values(self, values, skip_noise=False):
        return self._apply_values(values, skip_noise=skip_noise)

    def calculate_fields(self, fields):
        try:
            field1, field2 = fields
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Colourmap fields must contain exactly two arrays"
            ) from error
        return self._apply_fields(field1, field2)

    def update_from(self, source):
        for name in (
            "stops",
            "field1_name",
            "field2_name",
            "field1_positions",
            "field2_positions",
            "colour_grid",
            "field1_curve_points",
            "field1_curve_handles",
            "field2_curve_points",
            "field2_curve_handles",
            "noise_enabled",
        ):
            setattr(self, name, getattr(source, name))
        self.stops = self._normalize_stops(self.stops)
        self.field1_positions = self._normalize_positions(self.field1_positions)
        self.field2_positions = self._normalize_positions(self.field2_positions)
        self.colour_grid = self._normalize_grid(self.colour_grid)
        self.field1_curve_points = self._normalize_curve_points(
            self.field1_curve_points
        )
        self.field1_curve_handles = self._normalize_curve_handles(
            self.field1_curve_handles
        )
        self.field2_curve_points = self._normalize_curve_points(
            self.field2_curve_points
        )
        self.field2_curve_handles = self._normalize_curve_handles(
            self.field2_curve_handles
        )
        self.set_perlin_noise_transform(
            getattr(
                source.perlin_noise_transform,
                "block_object",
                source.perlin_noise_transform,
            )
        )
        self.prepare()
        self.mark_changed()
        return self

    def set_perlin_noise_transform(self, transform):
        """Replace the optional noise transform configuration reference."""
        if transform is not None and not isinstance(
            transform,
            PerlinNoiseTransformBlockObject,
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        if self.perlin_noise_transform is transform:
            return transform
        if self.perlin_noise_transform is not None:
            self.remove_change_child_block_object(self.perlin_noise_transform)
            self.perlin_noise_transform.remove_destruction_callback(
                self._on_noise_transform_destroyed
            )
        self.perlin_noise_transform = transform
        if transform is not None:
            self.add_change_child_block_object(transform)
            transform.add_destruction_callback(self._on_noise_transform_destroyed)
        self.mark_changed()
        return transform

    def _on_noise_transform_destroyed(self, transform):
        if transform is not self.perlin_noise_transform:
            return
        self.perlin_noise_transform = None
        self.noise_enabled = False
        self.remove_change_child_block_object(transform)
        self.mark_changed()

    def _on_child_destroyed(self, child, dependent=False):
        if child is self.perlin_noise_transform:
            self._on_noise_transform_destroyed(child)
            return
        super()._on_child_destroyed(child, dependent=dependent)

    def apply(self, values, skip_noise=False):
        """Map scalar values to interpolated RGBA colours."""
        self.prepare()
        return self._apply_values(values, skip_noise=skip_noise)

    def _apply_values(self, values, skip_noise=False):
        scalar_values = np.asarray(values, dtype=float)
        if (
            not skip_noise
            and self.noise_enabled
            and self.perlin_noise_transform is not None
        ):
            if scalar_values.ndim > 3:
                raise ValueError("Colourmap values must have at most 3 dimensions")
            field_shape = scalar_values.shape + (1,) * (3 - scalar_values.ndim)
            scalar_values = self.perlin_noise_transform.apply(
                scalar_values.reshape(field_shape)
            ).reshape(scalar_values.shape)
        positions = np.asarray([stop[0] for stop in self.stops])
        colours = np.asarray([stop[1] for stop in self.stops])
        clipped = np.clip(scalar_values, positions[0], positions[-1])
        channels = np.stack(
            [
                np.interp(clipped, positions, colours[:, channel])
                for channel in range(4)
            ],
            axis=-1,
        )
        return channels

    def apply_fields(self, field1, field2):
        """Sample the authored two-dimensional colour field at normalized inputs."""
        self.prepare()
        return self._apply_fields(field1, field2)

    def _apply_fields(self, field1, field2):
        first = np.clip(np.asarray(field1, dtype=float), 0.0, 1.0)
        second = np.clip(np.asarray(field2, dtype=float), 0.0, 1.0)
        if first.shape != second.shape:
            raise ValueError("Colourmap fields must have matching shapes")
        first = self._evaluate_curve(
            first, self.field1_curve_points, self.field1_curve_handles
        )
        second = self._evaluate_curve(
            second, self.field2_curve_points, self.field2_curve_handles
        )
        x_positions = np.asarray(self.field1_positions, dtype=float)
        y_positions = np.asarray(self.field2_positions, dtype=float)
        x_index = np.clip(
            np.searchsorted(x_positions, first, side="right") - 1,
            0,
            len(x_positions) - 2,
        )
        y_index = np.clip(
            np.searchsorted(y_positions, second, side="right") - 1,
            0,
            len(y_positions) - 2,
        )
        x_ratio = (first - x_positions[x_index]) / np.maximum(
            1e-12, x_positions[x_index + 1] - x_positions[x_index]
        )
        y_ratio = (second - y_positions[y_index]) / np.maximum(
            1e-12, y_positions[y_index + 1] - y_positions[y_index]
        )
        grid = np.asarray(self.colour_grid, dtype=float)
        top_left = grid[y_index, x_index]
        top_right = grid[y_index, x_index + 1]
        bottom_left = grid[y_index + 1, x_index]
        bottom_right = grid[y_index + 1, x_index + 1]
        top = (1.0 - x_ratio)[..., None] * top_left + x_ratio[..., None] * top_right
        bottom = (1.0 - x_ratio)[..., None] * bottom_left + x_ratio[
            ..., None
        ] * bottom_right
        return (1.0 - y_ratio)[..., None] * top + y_ratio[..., None] * bottom

    @staticmethod
    def _evaluate_curve(values, points, handles):
        if len(points) < 2:
            return values
        positions = np.asarray([point[0] for point in points], dtype=float)
        outputs = np.asarray([point[1] for point in points], dtype=float)
        segment = np.clip(
            np.searchsorted(positions, values, side="left") - 1,
            0,
            len(points) - 2,
        )
        local = (values - positions[segment]) / np.maximum(
            1e-12,
            positions[segment + 1] - positions[segment],
        )
        effective = []
        normalized_handles = list(handles)
        while len(normalized_handles) < len(points):
            normalized_handles.append(None)
        for index, point in enumerate(points):
            handle = normalized_handles[index]
            if handle is not None and len(handle) == 2:
                effective.append(handle)
                continue
            if index == 0:
                vector = (
                    (points[1][0] - point[0]) / 3.0,
                    (points[1][1] - point[1]) / 3.0,
                )
            elif index == len(points) - 1:
                vector = (
                    (point[0] - points[index - 1][0]) / 3.0,
                    (point[1] - points[index - 1][1]) / 3.0,
                )
            else:
                vector = (
                    (point[0] - points[index - 1][0]) / 3.0,
                    (point[1] - points[index - 1][1]) / 3.0,
                )
            effective.append(
                (
                    (point[0] - vector[0], point[1] - vector[1]),
                    (point[0] + vector[0], point[1] + vector[1]),
                )
            )
        control_start = np.asarray([pair[1][1] for pair in effective])[segment]
        control_end = np.asarray([pair[0][1] for pair in effective])[segment + 1]
        start = outputs[segment]
        end = outputs[segment + 1]
        minimum = np.minimum(start, end)
        maximum = np.maximum(start, end)
        control_start = np.clip(control_start, minimum, maximum)
        control_end = np.clip(control_end, minimum, maximum)
        inverse = 1.0 - local
        return (
            inverse**3 * start
            + 3.0 * inverse**2 * local * control_start
            + 3.0 * inverse * local**2 * control_end
            + local**3 * end
        )

    def serialise(self, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "guid": self.guid,
                    "comments": self.comments,
                    "field1_name": self.field1_name,
                    "field2_name": self.field2_name,
                    "field1_positions": list(self.field1_positions),
                    "field2_positions": list(self.field2_positions),
                    "colour_grid": [
                        [list(colour) for colour in row] for row in self.colour_grid
                    ],
                    "field1_curve_points": [
                        list(point) for point in self.field1_curve_points
                    ],
                    "field1_curve_handles": self._json_handles(
                        self.field1_curve_handles
                    ),
                    "field2_curve_points": [
                        list(point) for point in self.field2_curve_points
                    ],
                    "field2_curve_handles": self._json_handles(
                        self.field2_curve_handles
                    ),
                    "noise_enabled": self.noise_enabled,
                    "perlin_noise_transform_guid": (
                        None
                        if self.perlin_noise_transform is None
                        else self.perlin_noise_transform.guid
                    ),
                    "stops": [
                        {"position": position, "colour": list(colour)}
                        for position, colour in self.stops
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return output

    save = serialise

    def serialise_to_directory(self, directory):
        """Save this colourmap using its stable project block-data name."""
        return self.serialise(Path(directory) / f"{self.guid}.colourmap.json")

    @classmethod
    def load(cls, path: str | Path, **kwargs):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=data.get("name", "Colourmap"),
            guid=data.get("guid"),
            comments=data.get("comments", ""),
            field1_name=data.get("field1_name", "Field 1"),
            field2_name=data.get("field2_name", "Field 2"),
            field1_positions=tuple(data.get("field1_positions", (0.0, 1.0))),
            field2_positions=tuple(data.get("field2_positions", (0.0, 1.0))),
            colour_grid=tuple(
                tuple(tuple(colour) for colour in row)
                for row in data.get("colour_grid", ())
            ),
            field1_curve_points=tuple(
                tuple(point)
                for point in data.get("field1_curve_points", ((0.0, 0.0), (1.0, 1.0)))
            ),
            field1_curve_handles=tuple(data.get("field1_curve_handles", (None, None))),
            field2_curve_points=tuple(
                tuple(point)
                for point in data.get("field2_curve_points", ((0.0, 0.0), (1.0, 1.0)))
            ),
            field2_curve_handles=tuple(data.get("field2_curve_handles", (None, None))),
            noise_enabled=data.get("noise_enabled", True),
            stops=tuple(
                (item["position"], tuple(item["colour"]))
                for item in data.get("stops", ())
            ),
            **kwargs,
        )
