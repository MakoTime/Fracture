from dataclasses import dataclass

import numpy as np


@dataclass
class SurfaceMaskModel:
    """Editable boolean mask for one plane of a generated mesh."""

    axis: str
    shape: tuple[int, int]
    mask: np.ndarray | None = None

    def __post_init__(self):
        self.axis = self.axis.upper()
        self.shape = tuple(int(size) for size in self.shape)
        if len(self.shape) != 2 or any(size < 1 for size in self.shape):
            raise ValueError("surface mask shape must contain two positive dimensions")
        if self.mask is not None:
            values = np.asarray(self.mask, dtype=bool)
            if values.shape != self.shape:
                raise ValueError(f"mask must have shape {self.shape}")
            self.mask = values.copy()

    def values(self) -> np.ndarray:
        """Return the mask, treating an unconfigured mask as full."""
        if self.mask is None:
            return np.ones(self.shape, dtype=bool)
        return self.mask.copy()

    @property
    def view_axes(self) -> tuple[str, str]:
        """Return horizontal and vertical world axes for the canvas."""
        return {
            "X": ("Y", "Z"),
            "Y": ("X", "Z"),
            "Z": ("X", "Y"),
        }[self.axis]

    @property
    def _stored_axes(self) -> tuple[str, str]:
        return {
            "X": ("Y", "Z"),
            "Y": ("X", "Z"),
            "Z": ("X", "Y"),
        }[self.axis]

    @property
    def view_shape(self) -> tuple[int, int]:
        horizontal, vertical = self.view_axes
        dimensions = dict(zip(self._stored_axes, self.shape))
        return dimensions[vertical], dimensions[horizontal]

    def view_values(self) -> np.ndarray:
        return self.values().T[::-1, :]

    def set_view_values(self, values):
        values = np.asarray(values, dtype=bool)
        if values.shape != self.view_shape:
            raise ValueError(f"mask view must have shape {self.view_shape}")
        self.set_values(values[::-1, :].T)

    def set_values(self, values):
        values = np.asarray(values, dtype=bool)
        if values.shape != self.shape:
            raise ValueError(f"mask must have shape {self.shape}")
        self.mask = values.copy()
