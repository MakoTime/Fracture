from typing import Any
from pathlib import Path

import numpy as np
import pyvista as pv

from .mesh import MeshBlockObject
from .perlin_noise import PerlinNoiseTransformBlockObject


class GeneratedMeshBlockObject(MeshBlockObject):
    """Engine-owned mesh payload paired with a scalar grid field."""

    def __init__(
        self,
        mesh_data: Any = None,
        grid_data: Any = None,
        perlin_noise_transform=None,
        noise_enabled=True,
        **kwargs,
    ):
        super().__init__(mesh_data=mesh_data, **kwargs)
        self.grid_data = self._validate_grid_data(grid_data)
        self.mask_mesh_data = None
        self.grid_serialised_path: Path | None = None
        self.noise_enabled = bool(noise_enabled)
        if perlin_noise_transform is not None and not isinstance(
            perlin_noise_transform, PerlinNoiseTransformBlockObject
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        self.perlin_noise_transform = perlin_noise_transform
        if perlin_noise_transform is not None:
            self.add_child_block_object(perlin_noise_transform, dependent=True)

    def set_perlin_noise_transform(self, transform):
        if transform is not None and not isinstance(
            transform, PerlinNoiseTransformBlockObject
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        if self.perlin_noise_transform is not None:
            self.remove_child_block_object(self.perlin_noise_transform)
        self.perlin_noise_transform = transform
        if transform is not None:
            self.add_child_block_object(transform, dependent=True)
        return transform

    def _on_child_destroyed(self, child, dependent=False):
        if child is self.perlin_noise_transform:
            self.perlin_noise_transform = None
            self.noise_enabled = False
            self.remove_child_block_object(child)
            self.invalidate()
            return
        super()._on_child_destroyed(child, dependent=dependent)

    @staticmethod
    def _validate_grid_data(grid_data):
        if grid_data is None:
            grid_data = np.zeros((1, 1, 1), dtype=float)
        array = np.asarray(grid_data, dtype=float)
        if array.ndim != 3:
            raise ValueError("grid_data must be a three-dimensional scalar field")
        if not np.isfinite(array).all():
            raise ValueError("grid_data must contain only finite values")
        return array.copy()

    def set_grid_data(self, grid_data):
        self.grid_data = self._validate_grid_data(grid_data)
        return self.grid_data

    def serialise(self, path):
        """Save the mesh payload and its scalar grid beside each other."""
        output = super().serialise(path)
        grid_path = output.with_name(f"{self.guid}.grid.npy")
        np.save(grid_path, self.grid_data)
        self.grid_serialised_path = grid_path
        return output

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        grid_path: str | Path,
        name: str = "Generated Mesh",
        guid: str | None = None,
        comments: str = "",
        load_data: bool = True,
    ):
        payload_path = Path(path)
        scalar_path = Path(grid_path)
        return cls(
            mesh_data=pv.read(str(payload_path)) if load_data else None,
            grid_data=np.load(scalar_path, allow_pickle=False),
            name=name,
            guid=guid,
            comments=comments,
            serialised_path=payload_path,
        )
