from pathlib import Path
from typing import Any

import numpy as np
import pyvista as pv

from .mesh import MeshBlockObject
from .perlin_noise import PerlinNoiseTransformBlockObject


class ProceduralMeshBlock(MeshBlockObject):
    """Engine-owned marching-cubes mesh and scalar field for Perlin meshes."""

    def __init__(
        self,
        mesh_data: Any = None,
        grid_data: Any = None,
        perlin_noise_transform=None,
        **kwargs,
    ):
        super().__init__(mesh_data=mesh_data, **kwargs)
        self.grid_data = self._validate_grid_data(grid_data)
        self.grid_serialised_path: Path | None = None
        if perlin_noise_transform is not None and not isinstance(
            perlin_noise_transform, PerlinNoiseTransformBlockObject
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        self.perlin_noise_transform = perlin_noise_transform
        if perlin_noise_transform is not None:
            self.add_change_child_block_object(perlin_noise_transform)
            perlin_noise_transform.add_destruction_callback(
                self._on_noise_transform_destroyed
            )

    def set_perlin_noise_transform(self, transform, notify=True):
        if transform is not None and not isinstance(
            transform, PerlinNoiseTransformBlockObject
        ):
            raise TypeError(
                "perlin_noise_transform must be a PerlinNoiseTransformBlockObject"
            )
        if self.perlin_noise_transform is transform:
            return transform
        if self.perlin_noise_transform is not None:
            self.remove_change_child_block_object(self.perlin_noise_transform)
            self.perlin_noise_transform.remove_destruction_callback(
                self._on_noise_transform_destroyed
            )
        self.perlin_noise_transform = transform
        if transform is not None:
            self.add_change_child_block_object(transform)
            transform.add_destruction_callback(self._on_noise_transform_destroyed)
        if notify:
            self.mark_changed()
        return transform

    def _on_noise_transform_destroyed(self, transform):
        if transform is not self.perlin_noise_transform:
            return
        self.remove_change_child_block_object(transform)
        self.perlin_noise_transform = None
        self.mark_changed()

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

    def commit(self, result=None):
        if result is not None:
            self.set_grid_data(result["grid_data"])
            self.set_mesh_data(result["mesh_data"])
        return super().commit()

    def serialise(self, path):
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
        name: str = "Procedural Mesh",
        guid: str | None = None,
        comments: str = "",
        load_data: bool = True,
    ):
        payload_path = Path(path)
        return cls(
            mesh_data=pv.read(str(payload_path)) if load_data else None,
            grid_data=np.load(Path(grid_path), allow_pickle=False),
            name=name,
            guid=guid,
            comments=comments,
            serialised_path=payload_path,
        )


ProceduralMeshBlockObject = ProceduralMeshBlock
