from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from .base_block_object import BlockObject


@dataclass
class TransformBlockObject(BlockObject, ABC):
    """Engine-owned transformation that can modify scalar field data."""

    name: str = "Transform"
    guid: str = field(default_factory=lambda: str(uuid4()))
    comments: str = ""

    __hash__ = BlockObject.__hash__

    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)

    def prepare(self):
        return self

    def process(self, prepared, progress_callback=None):
        if progress_callback:
            progress_callback(1.0)
        self.validate()
        return self

    @abstractmethod
    def apply(self, values):
        """Return transformed values without mutating the input array."""

    def serialise(self, path):
        raise NotImplementedError(f"{type(self).__name__} must implement serialise()")

    save = serialise

    @classmethod
    def load(cls, path: str | Path, **kwargs):
        raise NotImplementedError(f"{type(cls).__name__} must implement load()")
