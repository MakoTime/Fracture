from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pyvista as pv


@dataclass
class SkyDome:
    """Configurable world-height gradient rendered behind scene objects."""

    radius: float = 10_000.0
    horizon_band: tuple[float, float] = (-0.12, 0.12)
    color_stops: tuple[tuple[int, int, int], ...] = field(
        default_factory=lambda: (
            (70, 85, 104),
            (70, 85, 104),
            (76, 112, 142),
            (23, 43, 70),
        )
    )
    actor: Any = field(default=None, init=False, repr=False)

    def add_to(self, plotter):
        """Create and add the dome actor to a PyVista plotter."""
        sky = pv.Sphere(
            radius=self.radius,
            center=(0.0, 0.0, 0.0),
            theta_resolution=64,
            phi_resolution=32,
        )
        sky["sky_color"] = self._colors(sky.points[:, 2] / self.radius)
        self.actor = plotter.add_mesh(
            sky,
            scalars="sky_color",
            rgb=True,
            lighting=False,
            show_scalar_bar=False,
            name="__sky_dome__",
            reset_camera=False,
        )
        self.actor.PickableOff()
        self.actor.UseBoundsOff()
        self.actor.GetProperty().BackfaceCullingOff()
        self.actor.GetProperty().FrontfaceCullingOff()
        plotter.camera.SetClippingRange(0.01, self.radius * 2.0)
        return self.actor

    def remove(self):
        """Forget the current actor after its plotter has been cleared."""
        self.actor = None

    def _colors(self, height):
        stops = np.array(
            [-1.0, self.horizon_band[0], self.horizon_band[1], 1.0]
        )
        colors = np.asarray(self.color_stops, dtype=float)
        if colors.shape != (4, 3):
            raise ValueError("color_stops must contain four RGB colors")
        return np.column_stack(
            [np.interp(height, stops, colors[:, channel]) for channel in range(3)]
        ).astype(np.uint8)
