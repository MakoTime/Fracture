import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from .base_block_object import BlockObject
from src.common.calendar import WorldTime


@dataclass
class DatetimeRow:
    name: str
    date: WorldTime

    @staticmethod
    def from_dict(data: dict):
        return DatetimeRow(
            name=data.get("name", ""),
            date=WorldTime.from_dict(data["date"])
            if "date" in data
            else WorldTime.now(),
        )

    def to_dict(self):
        return {
            "name": self.name,
            "date": self.date.to_dict(),
        }


@dataclass
class SavedTimes:
    rows: list[DatetimeRow] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        return SavedTimes(
            rows=[DatetimeRow.from_dict(row) for row in data.get("rows", [])]
        )

    def to_dict(self):
        return {"rows": [row.to_dict() for row in self.rows]}


@dataclass
class WorldStateBlockObject(BlockObject):
    """Engine-owned configuration for the active world."""

    name: str = "World State"
    guid: str = field(default_factory=lambda: str(uuid4()))
    comments: str = ""
    date_time: WorldTime = field(default_factory=WorldTime.now)
    saved_times: SavedTimes = field(default_factory=SavedTimes)

    __hash__ = BlockObject.__hash__

    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)

    def __setattr__(self, name, value):
        if name == "date_time" and isinstance(value, dict):
            value = WorldTime.from_dict(value)
        if name == "date_time" and not isinstance(value, WorldTime):
            raise TypeError("date_time must be a WorldTime instance")
        elif name == "saved_times" and isinstance(value, dict):
            value = SavedTimes.from_dict(value)
        super().__setattr__(name, value)

    def prepare(self):
        return self

    def process(self, prepared, progress_callback=None):
        self.date_time = prepared["date_time"]
        self.saved_times = prepared["saved_times"]
        if progress_callback:
            progress_callback(1.0)
        self.validate()
        return self

    def update_configuration(self, *, name=None, date_time=None, saved_times=None):
        if name is not None:
            self.name = str(name).strip() or "World State"
        if date_time is not None:
            self.date_time = date_time
        if saved_times is not None:
            self.saved_times = saved_times
        self.mark_changed()
        return self

    def serialise(self, path):
        path = Path(path)
        path.write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")
        return path

    def serialise_to_directory(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return self.serialise(directory / f"{self.guid}.world_state.json")

    def to_json(self):
        return {
            "type": "world_state",
            "name": self.name,
            "guid": self.guid,
            "comments": self.comments,
            "date_time": self.date_time.to_dict(),
            "saved_times": self.saved_times.to_dict(),
        }

    @classmethod
    def load(cls, path, **kwargs):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=data.get("name", "World State"),
            guid=data.get("guid"),
            comments=data.get("comments", ""),
            date_time=WorldTime.from_dict(data["date_time"])
            if "date_time" in data
            else WorldTime.now(),
            saved_times=SavedTimes.from_dict(data.get("saved_times", {})),
            **kwargs,
        )


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
