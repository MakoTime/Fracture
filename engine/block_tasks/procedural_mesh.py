from dataclasses import replace

import numpy as np
import pyvista as pv

from engine.block_objects import ProceduralMeshBlock
from engine.block_objects import PerlinNoiseTransformBlockObject


class ProceduralMeshTask:
    """Generate a scalar grid and marching-cubes surface from Perlin noise."""

    def __init__(self, model, block_object=None):
        self.model = model
        self.grid_data = None
        self.block_object = block_object or ProceduralMeshBlock(
            name=model.name.strip() or "Procedural Mesh",
            guid=model.guid,
            perlin_noise_transform=self._perlin_noise_block(),
        )

    def _perlin_noise_block(self):
        transform = getattr(self.model, "perlin_noise_transform", None)
        if transform is None:
            return None
        if isinstance(transform, PerlinNoiseTransformBlockObject):
            return transform
        if hasattr(transform, "block_object"):
            return transform.block_object
        return transform.to_object().block_object

    def prepare(self):
        transform = self.block_object.perlin_noise_transform
        transform_prepared = None if transform is None else transform.prepare()
        if transform_prepared is not None and self.model.seed is not None:
            transform_prepared = replace(
                transform_prepared,
                seed=int(self.model.seed),
            )
        dimensions = tuple(max(1, int(value)) for value in self.model.grid_size)
        lower_threshold = float(self.model.lower_threshold)
        upper_threshold = float(self.model.upper_threshold)
        if not np.isfinite(
            [lower_threshold, upper_threshold]
        ).all():
            raise ValueError("procedural mesh settings must be finite")
        if lower_threshold > upper_threshold:
            raise ValueError("lower_threshold must not exceed upper_threshold")
        return {
            "dimensions": dimensions,
            "transform": transform_prepared,
            "lower_threshold": lower_threshold,
            "upper_threshold": upper_threshold,
        }

    def process(self, prepared, progress_callback=None):
        report = progress_callback or (lambda progress: None)
        report(0.0)
        dimensions = prepared["dimensions"]
        transform = self.block_object.perlin_noise_transform
        if transform is None:
            grid_data = np.zeros(dimensions, dtype=float)
        else:
            grid_data = transform._build_noise_field(
                dimensions,
                prepared["transform"],
            )
        report(0.5)
        selected = (
            (grid_data >= prepared["lower_threshold"])
            & (grid_data <= prepared["upper_threshold"])
        )
        grid_data = np.where(selected, grid_data, 0.0)
        mesh = self._build_surface_mesh(grid_data)
        self.grid_data = grid_data
        report(1.0)
        return {"grid_data": grid_data, "mesh_data": mesh}

    @staticmethod
    def _build_surface_mesh(grid_data):
        values = np.asarray(grid_data, dtype=float)
        if not np.any(values > 0.0):
            return pv.PolyData()
        padded = np.pad(values, 1, constant_values=0.0)
        image = pv.ImageData(
            dimensions=padded.shape,
            spacing=(1.0, 1.0, 1.0),
        )
        image.point_data["values"] = padded.ravel(order="F")
        surface = image.contour(isosurfaces=[1e-6], scalars="values")
        surface.translate((-1.0, -1.0, -1.0), inplace=True)
        return surface

    def execute(self, prepared, progress_callback=None):
        result = self.process(prepared, progress_callback)
        self.block_object.commit(result)
        self.grid_data = self.block_object.grid_data
        return self.block_object


class ProceduralMeshObjectTask:
    """Regenerate an existing procedural-mesh block in place."""

    def __init__(self, model, block_object):
        self.model = model
        self.block_object = block_object

    def prepare(self):
        generation_task = ProceduralMeshTask(self.model, self.block_object)
        return {
            "transform": self._perlin_noise_block(),
            "generation": generation_task.prepare(),
        }

    def process(self, prepared, progress_callback=None):
        transform = prepared["transform"]
        self.block_object.set_perlin_noise_transform(transform)
        if transform is not None:
            self.model.perlin_noise_transform = transform
        generation_task = ProceduralMeshTask(self.model, self.block_object)
        return generation_task.process(prepared["generation"], progress_callback)

    def execute(self, prepared, progress_callback=None):
        result = self.process(prepared, progress_callback)
        self.block_object.commit(result)
        return self.block_object

    def _perlin_noise_block(self):
        transform = getattr(self.model, "perlin_noise_transform", None)
        if transform is None:
            return None
        if isinstance(transform, PerlinNoiseTransformBlockObject):
            candidate = transform
        elif hasattr(transform, "block_object"):
            candidate = transform.block_object
        else:
            candidate = transform.to_object().block_object
        current = self.block_object.perlin_noise_transform
        if current is not None and current.guid == candidate.guid:
            return current
        return candidate
