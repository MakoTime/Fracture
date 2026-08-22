import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from .base_block_object import BlockObject


@dataclass
class WorldConfigBlockObject(BlockObject):
    """Engine-owned configuration for the active world."""

    name: str = "World Config"
    centre: tuple[float, float, float] = (0.0, 0.0, 0.0)
    guid: str = field(default_factory=lambda: str(uuid4()))
    comments: str = ""

    __hash__ = BlockObject.__hash__

    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)
        self.centre = self._normalize_centre(self.centre)

    @staticmethod
    def _normalize_centre(centre):
        values = tuple(float(value) for value in centre)
        if len(values) != 3:
            raise ValueError("centre must contain three values")
        return values

    def update_configuration(self, *, name=None, centre=None):
        if name is not None:
            self.name = str(name).strip() or "World Config"
        if centre is not None:
            self.centre = self._normalize_centre(centre)
        self.mark_changed()
        return self

    def prepare(self):
        return self

    def process(self, prepared, progress_callback=None):
        if progress_callback:
            progress_callback(1.0)
        self.validate()
        return self

    def serialise(self, path):
        path = Path(path)
        path.write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")
        return path

    def serialise_to_directory(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return self.serialise(directory / f"{self.guid}.world_config.json")

    def to_json(self):
        return {
            "type": "world_config",
            "name": self.name,
            "centre": list(self.centre),
            "guid": self.guid,
            "comments": self.comments,
        }

    @classmethod
    def load(cls, path, **kwargs):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=data.get("name", "World Config"),
            centre=tuple(data.get("centre", (0.0, 0.0, 0.0))),
            guid=data.get("guid"),
            comments=data.get("comments", ""),
            **kwargs,
        )