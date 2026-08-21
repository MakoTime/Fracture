from dataclasses import dataclass, field
from uuid import uuid4

from engine.block_objects import ColourmapBlockObject
from objects.colourmap import ColourmapObject
from tools.widgets.bezier_graph import normalize_curve_handles, normalize_curve_points


@dataclass
class ColourmapModel:
    """Editable settings for a scalar-to-RGBA colourmap."""

    name: str = "Colourmap"
    field1_name: str = "Field 1"
    field2_name: str = "Field 2"
    stops: tuple = (
        (0.0, (0.0, 0.0, 0.0, 1.0)),
        (1.0, (1.0, 1.0, 1.0, 1.0)),
    )
    field1_positions: tuple[float, ...] = (0.0, 1.0)
    field2_positions: tuple[float, ...] = (0.0, 1.0)
    colour_grid: tuple = ()
    field1_curve_points: tuple = ((0.0, 0.0), (1.0, 1.0))
    field1_curve_handles: tuple = (None, None)
    field2_curve_points: tuple = ((0.0, 0.0), (1.0, 1.0))
    field2_curve_handles: tuple = (None, None)
    comments: str = ""
    noise_enabled: bool = False
    perlin_noise_transform: object | None = None
    guid: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        self.stops = ColourmapBlockObject._normalize_stops(self.stops)
        self.field1_name = self.field1_name.strip() or "Field 1"
        self.field2_name = self.field2_name.strip() or "Field 2"
        self.field1_positions = self._normalize_positions(self.field1_positions)
        self.field2_positions = self._normalize_positions(self.field2_positions)
        if not self.colour_grid:
            self.colour_grid = self._grid_from_stops(self.stops)
        self.colour_grid = self._normalize_grid(self.colour_grid)
        self.field1_curve_points = normalize_curve_points(self.field1_curve_points)
        self.field1_curve_handles = normalize_curve_handles(self.field1_curve_handles)
        self.field2_curve_points = normalize_curve_points(self.field2_curve_points)
        self.field2_curve_handles = normalize_curve_handles(self.field2_curve_handles)
        self.noise_enabled = bool(self.noise_enabled)

    @staticmethod
    def _normalize_positions(positions):
        values = tuple(sorted(float(value) for value in positions))
        if len(values) < 2 or values[0] < 0.0 or values[-1] > 1.0:
            raise ValueError("Each colourmap field requires at least two positions between 0 and 1")
        if len(set(values)) != len(values):
            raise ValueError("Colourmap field positions must be unique")
        return values

    def _grid_from_stops(self, stops):
        colours = tuple(colour for _, colour in stops)
        return tuple(
            tuple(colours[index % len(colours)] for index in range(len(self.field1_positions)))
            for _ in self.field2_positions
        )

    def _normalize_grid(self, grid):
        if len(grid) != len(self.field2_positions) or any(
            len(row) != len(self.field1_positions) for row in grid
        ):
            raise ValueError("Colourmap colour grid must match both field position lists")
        normalized = []
        for row in grid:
            normalized_row = []
            for colour in row:
                rgba = tuple(float(channel) for channel in colour)
                if len(rgba) == 3:
                    rgba += (1.0,)
                if len(rgba) != 4 or any(channel < 0.0 or channel > 1.0 for channel in rgba):
                    raise ValueError("Colourmap colours must be RGB or RGBA values between 0 and 1")
                normalized_row.append(rgba)
            normalized.append(tuple(normalized_row))
        return tuple(normalized)

    def to_object(self):
        transform = self.perlin_noise_transform
        if hasattr(transform, "block_object"):
            transform = transform.block_object
        block = ColourmapBlockObject(
            name=self.name.strip() or "Colourmap",
            guid=self.guid,
            comments=self.comments,
            field1_name=self.field1_name,
            field2_name=self.field2_name,
            field1_positions=self.field1_positions,
            field2_positions=self.field2_positions,
            colour_grid=self.colour_grid,
            field1_curve_points=self.field1_curve_points,
            field1_curve_handles=self.field1_curve_handles,
            field2_curve_points=self.field2_curve_points,
            field2_curve_handles=self.field2_curve_handles,
            stops=self.stops,
            noise_enabled=self.noise_enabled,
            perlin_noise_transform=transform,
        )
        return ColourmapObject(
            name=self.name.strip() or "Colourmap",
            block_object=block,
            comments=self.comments,
            guid=self.guid,
            auto_register_root=False,
        )

    @classmethod
    def from_object(cls, colourmap):
        block = colourmap.block_object
        return cls(
            name=colourmap.name,
            stops=block.stops,
            field1_positions=getattr(block, "field1_positions", (0.0, 1.0)),
            field2_positions=getattr(block, "field2_positions", (0.0, 1.0)),
            colour_grid=getattr(block, "colour_grid", ()),
            field1_curve_points=getattr(block, "field1_curve_points", ((0.0, 0.0), (1.0, 1.0))),
            field1_curve_handles=getattr(block, "field1_curve_handles", (None, None)),
            field2_curve_points=getattr(block, "field2_curve_points", ((0.0, 0.0), (1.0, 1.0))),
            field2_curve_handles=getattr(block, "field2_curve_handles", (None, None)),
            comments=block.comments,
            field1_name=getattr(block, "field1_name", "Field 1"),
            field2_name=getattr(block, "field2_name", "Field 2"),
            noise_enabled=block.noise_enabled,
            perlin_noise_transform=block.perlin_noise_transform,
            guid=colourmap.guid,
        )

    @classmethod
    def from_json(cls, data):
        return cls(
            name=data.get("name", "Colourmap"),
            stops=tuple(
                (item["position"], tuple(item["colour"]))
                for item in data.get("stops", ())
            ),
            comments=data.get("comments", ""),
            field1_name=data.get("field1_name", "Field 1"),
            field2_name=data.get("field2_name", "Field 2"),
            noise_enabled=data.get("noise_enabled", False),
            guid=data.get("guid", str(uuid4())),
            field1_positions=tuple(data.get("field1_positions", (0.0, 1.0))),
            field2_positions=tuple(data.get("field2_positions", (0.0, 1.0))),
            colour_grid=tuple(
                tuple(tuple(colour) for colour in row)
                for row in data.get("colour_grid", ())
            ),
            field1_curve_points=tuple(tuple(point) for point in data.get("field1_curve_points", ((0.0, 0.0), (1.0, 1.0)))),
            field1_curve_handles=tuple(data.get("field1_curve_handles", (None, None))),
            field2_curve_points=tuple(tuple(point) for point in data.get("field2_curve_points", ((0.0, 0.0), (1.0, 1.0)))),
            field2_curve_handles=tuple(data.get("field2_curve_handles", (None, None))),
        )

    def to_json(self):
        return {
            "type": "colourmap",
            "name": self.name,
            "guid": self.guid,
            "comments": self.comments,
            "field1_name": self.field1_name,
            "field2_name": self.field2_name,
            "noise_enabled": self.noise_enabled,
            "perlin_noise_transform_guid": (
                None
                if self.perlin_noise_transform is None
                else getattr(
                    getattr(self.perlin_noise_transform, "block_object", self.perlin_noise_transform),
                    "guid",
                    None,
                )
            ),
            "stops": [
                {"position": position, "colour": list(colour)}
                for position, colour in self.stops
            ],
            "field1_positions": list(self.field1_positions),
            "field2_positions": list(self.field2_positions),
            "colour_grid": [
                [list(colour) for colour in row] for row in self.colour_grid
            ],
            "field1_curve_points": [list(point) for point in self.field1_curve_points],
            "field1_curve_handles": self._json_handles(self.field1_curve_handles),
            "field2_curve_points": [list(point) for point in self.field2_curve_points],
            "field2_curve_handles": self._json_handles(self.field2_curve_handles),
        }

    @staticmethod
    def _json_handles(handles):
        return [
            None if handle is None else [list(point) for point in handle]
            for handle in handles
        ]
