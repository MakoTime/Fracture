from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

from .base_block_object import BlockObject
from .mesh import MeshBlockObject
from .world_config import WorldConfigBlockObject


@dataclass
class IslandBlockObject(BlockObject):
    """Engine-owned island mesh positioned from a source mesh and world config."""

    mesh_block: MeshBlockObject | None = None
    world_config: WorldConfigBlockObject | None = None
    core_offset: float = 0.0
    orbit_speed: float = 0.0
    orbit_normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    orbit_angle: float = 0.0
    curve_mesh: bool = False
    mesh_data: Any = None
    name: str = "Island"
    guid: str = field(default_factory=lambda: str(uuid4()))
    comments: str = ""
    serialised_path: Path | None = field(default=None, repr=False, compare=False)

    __hash__ = BlockObject.__hash__

    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)
        self.core_offset = self._normalize_core_offset(self.core_offset)
        self.orbit_speed = float(self.orbit_speed)
        self.orbit_normal = self._normalize_orbit_normal(self.orbit_normal)
        self.orbit_angle = float(self.orbit_angle)
        self.curve_mesh = bool(self.curve_mesh)
        self.set_mesh_block(self.mesh_block, notify=False)
        self.set_world_config(self.world_config, notify=False)

    def set_mesh_block(self, mesh_block, notify=True):
        if mesh_block is not None and not isinstance(mesh_block, MeshBlockObject):
            raise TypeError("mesh_block must be a MeshBlockObject")
        if self.mesh_block is not None:
            self.remove_child_block_object(self.mesh_block)
            self.mesh_block.remove_destruction_callback(self._on_mesh_block_destroyed)
        self.mesh_block = mesh_block
        if mesh_block is not None:
            self.add_child_block_object(mesh_block)
            mesh_block.add_destruction_callback(self._on_mesh_block_destroyed)
        if notify:
            self.mark_changed()
        return mesh_block

    def set_world_config(self, world_config, notify=True):
        if world_config is not None and not isinstance(
            world_config, WorldConfigBlockObject
        ):
            raise TypeError("world_config must be a WorldConfigBlockObject")
        if self.world_config is not None:
            self.remove_change_child_block_object(self.world_config)
            self.world_config.remove_destruction_callback(
                self._on_world_config_destroyed
            )
        self.world_config = world_config
        if world_config is not None:
            self.add_change_child_block_object(world_config)
            world_config.add_destruction_callback(self._on_world_config_destroyed)
        if notify:
            self.mark_changed()
        return world_config

    @staticmethod
    def _normalize_core_offset(core_offset):
        if isinstance(core_offset, (tuple, list)):
            values = tuple(float(value) for value in core_offset)
            if len(values) != 3:
                raise ValueError("core_offset must be a radius")
            core_offset = sum(value * value for value in values) ** 0.5
        radius = float(core_offset)
        if radius < 0.0 or radius != radius or abs(radius) == float("inf"):
            raise ValueError("core_offset must be a finite non-negative radius")
        return radius

    @staticmethod
    def _normalize_orbit_normal(orbit_normal):
        values = np.asarray(orbit_normal, dtype=float)
        if values.shape != (3,) or not np.isfinite(values).all():
            raise ValueError("orbit_normal must contain three finite values")
        length = np.linalg.norm(values)
        if length <= 1e-12:
            raise ValueError("orbit_normal must not be zero")
        return tuple((values / length).tolist())

    def _on_mesh_block_destroyed(self, mesh_block):
        if mesh_block is self.mesh_block:
            self.mesh_block = None
            self._mark_changed({}, invalidates=False)

    def _on_world_config_destroyed(self, world_config):
        if world_config is self.world_config:
            self.world_config = None
            self._mark_changed({}, invalidates=False)

    def update_configuration(
        self,
        *,
        core_offset=None,
        orbit_speed=None,
        orbit_normal=None,
        orbit_angle=None,
        curve_mesh=None,
    ):
        if core_offset is not None:
            self.core_offset = self._normalize_core_offset(core_offset)
        if orbit_speed is not None:
            self.orbit_speed = float(orbit_speed)
        if orbit_normal is not None:
            self.orbit_normal = self._normalize_orbit_normal(orbit_normal)
        if orbit_angle is not None:
            self.orbit_angle = float(orbit_angle)
        if curve_mesh is not None:
            self.curve_mesh = bool(curve_mesh)
        self.mark_changed()
        return self

    def prepare(self):
        if self.mesh_block is None:
            raise ValueError("Island requires a mesh block")
        if self.world_config is None:
            raise ValueError("Island requires a world config")
        return {
            "mesh_data": self.mesh_block.scene_data,
            "centre": tuple(self.world_config.centre),
            "core_offset": self.core_offset,
            "orbit_speed": self.orbit_speed,
            "orbit_normal": self.orbit_normal,
            "orbit_angle": self.orbit_angle,
            "curve_mesh": self.curve_mesh,
        }

    def orbit_angle_at_time(self, elapsed_seconds):
        """Return the current orbit angle in degrees for elapsed time."""
        return self.orbit_angle + self.orbit_speed * float(elapsed_seconds)

    def orbit_transform_at_time(self, elapsed_seconds):
        """Return an actor transform without rebuilding the Island mesh."""
        from engine.block_tasks.island import _orbit_frame

        centre = np.asarray(self.world_config.centre, dtype=float)
        initial_radial, initial_tangent, initial_up = _orbit_frame(
            np.asarray(self.orbit_normal), self.orbit_angle
        )
        current_radial, current_tangent, current_up = _orbit_frame(
            np.asarray(self.orbit_normal),
            self.orbit_angle_at_time(elapsed_seconds),
        )
        initial_frame = np.column_stack((initial_tangent, initial_up, initial_radial))
        current_frame = np.column_stack((current_tangent, current_up, current_radial))
        linear = current_frame @ initial_frame.T
        initial_position = centre + self.core_offset * initial_radial
        current_position = centre + self.core_offset * current_radial
        transform = np.eye(4)
        transform[:3, :3] = linear
        transform[:3, 3] = current_position - linear @ initial_position
        return transform

    def process(self, prepared, progress_callback=None):
        from engine.block_tasks.island import build_island_mesh

        result = build_island_mesh(prepared)
        if progress_callback:
            progress_callback(1.0)
        return result

    def commit(self, result=None):
        self.mesh_data = result
        self.validate()
        return self

    def set_mesh_data(self, mesh_data):
        """Cache a renderable-adjusted copy so
        normals aren't recomputed every render.
        """

        self.mesh_data = mesh_data
        return mesh_data

    @property
    def scene_data(self):
        if self.mesh_data is None and self.serialised_path is not None:
            import pyvista as pv

            self.mesh_data = pv.read(str(self.serialised_path))
        return self.mesh_data

    @property
    def colourmap(self):
        return self.mesh_block.colourmap if self.mesh_block is not None else None

    @property
    def colourmap_scope(self):
        if self.mesh_block is None:
            return "local"
        return self.mesh_block.colourmap_scope

    @property
    def colourmap_field_sources(self):
        if self.mesh_block is None:
            return ("elevation", "normal_z")
        return self.mesh_block.colourmap_field_sources

    @property
    def colourmap_field_inversions(self):
        if self.mesh_block is None:
            return (False, False)
        return self.mesh_block.colourmap_field_inversions

    @property
    def colourmap_reference_data(self):
        """Return the untransformed source mesh driving local colourmap fields."""
        if self.mesh_block is None:
            return self.scene_data
        return self.mesh_block.scene_data

    def serialise(self, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if self.mesh_data is None:
            if self.serialised_path is None or not self.serialised_path.exists():
                raise ValueError("Cannot save an unprocessed island block")
            if self.serialised_path.resolve() != output.resolve():
                import shutil

                shutil.copy2(self.serialised_path, output)
        else:
            self.mesh_data.save(str(output))
        self.serialised_path = output
        return output

    def serialise_to_directory(self, directory):
        return self.serialise(Path(directory) / f"{self.guid}.vtp")
