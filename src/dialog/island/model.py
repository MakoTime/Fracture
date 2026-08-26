from dataclasses import dataclass, field

import numpy as np
import pyvista as pv

from src.common.calendar import WorldTime
from src.dialog.base.editor import EditorModel
from src.engine.block_tasks.island import build_island_mesh


@dataclass
class IslandModel(EditorModel):
    """Editable Island placement and preview state."""

    island: object
    name: str = "Island"
    source_mesh: object | None = None
    source_meshes: tuple = ()
    core_offset: float = 0.0
    orbit_speed: float = 0.0
    orbit_normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    orbit_angle: float = 0.0
    curve_mesh: bool = False
    show_in_place: bool = False
    show_path: bool = False
    show_in_scene: bool = True
    reference_time: WorldTime = field(default_factory=WorldTime.now, repr=False, compare=False)

    @classmethod
    def from_island(cls, island):
        block = island.block_object
        return cls(
            island=island,
            name=island.name,
            source_mesh=None,
            core_offset=block.core_offset,
            orbit_speed=block.orbit_speed,
            orbit_normal=block.orbit_normal,
            orbit_angle=block.orbit_angle,
            curve_mesh=block.curve_mesh,
            show_in_scene=getattr(
                island,
                "show_in_scene",
                island._scene is not None,
            ),
            reference_time=block.reference_time if hasattr(block, "reference_time") else WorldTime.now(),
        )

    def set_source_meshes(self, source_meshes):
        self.source_meshes = tuple(source_meshes)
        current_block = self.island.block_object.mesh_block
        matching_mesh = next(
            (
                mesh
                for mesh in self.source_meshes
                if getattr(mesh, "block_object", mesh) is current_block
            ),
            None,
        )
        if matching_mesh is not None:
            self.source_mesh = matching_mesh
        elif self.source_mesh is None and self.source_meshes:
            self.source_mesh = self.source_meshes[0]
        return self.source_meshes

    def validate(self):
        if self.source_mesh is None and self.island.block_object.mesh_block is None:
            raise ValueError("an Island source mesh must be selected")
        radius = float(self.core_offset)
        if radius < 0.0 or not np.isfinite(radius):
            raise ValueError("core offset must be a finite non-negative radius")
        self.core_offset = radius
        self.orbit_speed = float(self.orbit_speed)
        self.orbit_angle = float(self.orbit_angle)
        self.orbit_normal = self.island.block_object._normalize_orbit_normal(
            self.orbit_normal
        )
        if not np.isfinite((self.orbit_speed, self.orbit_angle)).all():
            raise ValueError("orbit angle and speed must be finite")

    def apply(self):
        self.validate()
        name = self.name.strip() or "Island"
        self.island._on_name_changed(name)
        self.island.block_object.name = name
        self.island.block_object.update_configuration(
            core_offset=self.core_offset,
            orbit_speed=self.orbit_speed,
            orbit_normal=self.orbit_normal,
            orbit_angle=self.orbit_angle,
            curve_mesh=self.curve_mesh,
        )
        source = self.source_mesh or self.island.block_object.mesh_block
        source_block = getattr(source, "block_object", source)
        self.island.block_object.set_mesh_block(source_block)
        self.island.show_in_scene = self.show_in_scene
        return self.island

    def preview_mesh(self, elapsed_seconds=0.0):
        block = self.island.block_object
        source = self.source_mesh or block.mesh_block
        if source is None:
            return None
        self.validate()
        source_block = getattr(source, "block_object", source)
        return build_island_mesh(
            {
                "mesh_data": source_block.scene_data,
                "centre": tuple(block.world_config.centre),
                "core_offset": self.core_offset,
                "orbit_phase": self.orbit_speed * float(elapsed_seconds),
                "orbit_normal": self.orbit_normal,
                "orbit_angle": self.orbit_angle,
                "curve_mesh": self.curve_mesh,
                "reference_time": self.reference_time,
            },
            self.reference_time,
        )

    def core_point(self):
        return pv.PolyData(np.asarray(self.island.block_object.world_config.centre))

    def path(self, samples=96):
        self.validate()
        centre = np.asarray(self.island.block_object.world_config.centre)
        radius = float(self.core_offset)
        if radius <= 1e-12:
            return pv.PolyData(centre)
        angles = np.linspace(0.0, 360.0, samples)
        points = []
        for orbit_angle in angles:
            prepared = {
                "mesh_data": pv.PolyData(np.zeros((1, 3))),
                "centre": centre,
                "core_offset": radius,
                "orbit_normal": self.orbit_normal,
                "orbit_angle": orbit_angle,
                "curve_mesh": self.curve_mesh,
                "reference_time": self.reference_time,
            }
            points.append(build_island_mesh(prepared).center)
        return pv.lines_from_points(np.asarray(points), close=False)
