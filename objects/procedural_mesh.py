from typing import Any

import numpy as np
from PySide6.QtGui import QIcon

from engine.block_objects import ProceduralMeshBlock

from .mesh_object import MeshObject


class ProceduralMeshObject(MeshObject):
    """Application object representing a Perlin-noise marching-cubes mesh."""

    def __init__(
        self,
        name: str,
        grid_data: Any = None,
        mesh_data: Any = None,
        block_object: ProceduralMeshBlock | None = None,
        comments: str = "",
        visible: bool = False,
        icon: QIcon | None = None,
        guid: str | None = None,
        auto_register_root: bool = False,
    ):
        if block_object is not None and not isinstance(
            block_object, ProceduralMeshBlock
        ):
            raise TypeError("ProceduralMeshObject requires a ProceduralMeshBlock")
        validated_grid_data = (
            block_object.grid_data.copy()
            if grid_data is None and block_object is not None
            else self._validate_grid_data(grid_data)
        )
        block = block_object or ProceduralMeshBlock(
            mesh_data=mesh_data,
            grid_data=validated_grid_data,
        )
        block.set_grid_data(validated_grid_data)
        super().__init__(
            name=name,
            block_object=block,
            comments=comments,
            icon=icon,
            visible=visible,
            guid=guid,
            auto_register_root=auto_register_root,
        )
        self.metadata["grid_shape"] = self.grid_data.shape

    @property
    def grid_data(self):
        return self.mesh_block_object.grid_data

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.grid_data.shape

    def set_grid_data(self, grid_data):
        self.mesh_block_object.set_grid_data(grid_data)
        self.metadata["grid_shape"] = self.grid_data.shape
        return self.grid_data

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


ProceduralMesh = ProceduralMeshObject
