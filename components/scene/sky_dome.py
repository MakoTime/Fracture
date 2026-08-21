from dataclasses import dataclass, field
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
    plotter: object | None = field(default=None, init=False, repr=False)

    def add_to(self, plotter):
        """Configure PyVista's renderer-level gradient background."""
        plotter.set_background(
            self.color_stops[0],
            top=self.color_stops[-1],
            all_renderers=False,
        )
        self.plotter = plotter
        return plotter.renderer

    def remove(self):
        """Release the plotter reference after a renderer reset."""
        self.plotter = None

