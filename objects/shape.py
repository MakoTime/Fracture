from dataclasses import dataclass, field
from typing import Any


@dataclass
class Shape:
    """A lightweight scene annotation owned by a normal project object."""

    kind: str
    data: Any
    name: str = "Shape"
    style: dict[str, Any] = field(default_factory=dict)
    visible: bool = True

    @classmethod
    def line(cls, points, name="Line", **style):
        return cls("line", points, name=name, style=style)

    @classmethod
    def text(cls, value, position, name="Text", **style):
        return cls("text", (value, position), name=name, style=style)

    @classmethod
    def mesh(cls, data, name="Shape", **style):
        return cls("mesh", data, name=name, style=style)