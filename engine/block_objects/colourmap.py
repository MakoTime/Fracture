from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import json

import numpy as np

from .base_block_object import BlockObject


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
    guid: str | None = None
    comments: str = ""

    __hash__ = BlockObject.__hash__

    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)
        self.stops = self._normalize_stops(self.stops)

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
            for (position, _), (next_position, _) in zip(
                normalized, normalized[1:]
            )
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
        return self

    def process(self, progress_callback=None):
        self.prepare()
        if progress_callback:
            progress_callback(1.0)
        return self

    def apply(self, values):
        """Map scalar values to an array of interpolated RGBA colours."""
        scalar_values = np.asarray(values, dtype=float)
        positions = np.asarray([stop[0] for stop in self.stops])
        colours = np.asarray([stop[1] for stop in self.stops])
        clipped = np.clip(scalar_values, positions[0], positions[-1])
        channels = np.stack(
            [np.interp(clipped, positions, colours[:, channel]) for channel in range(4)],
            axis=-1,
        )
        return channels

    def serialise(self, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "guid": self.guid,
                    "comments": self.comments,
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

    @classmethod
    def load(cls, path: str | Path, **kwargs):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=data.get("name", "Colourmap"),
            guid=data.get("guid"),
            comments=data.get("comments", ""),
            stops=tuple(
                (item["position"], tuple(item["colour"]))
                for item in data.get("stops", ())
            ),
            **kwargs,
        )
