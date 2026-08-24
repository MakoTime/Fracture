from dataclasses import replace

import numpy as np
import pyvista as pv

from src.engine.block_objects import (
    PerlinNoiseTransformBlockObject,
    ProceduralMeshBlock,
)


class ProceduralMeshTask:
    """Generate a scalar grid and marching-cubes surface from Perlin noise."""

    def __init__(self, model, block_object=None):
        self.model = model
        self.grid_data = None
        self.block_object = block_object or ProceduralMeshBlock(
            name=model.name.strip() or "Procedural Mesh",
            guid=model.guid,
            perlin_noise_transform=self._perlin_noise_block(),
            dropoff_data=model.dropoff_dimensions,
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
        amplitudes = (
            self.model.dropoff_dimensions.x.amplitudes,
            self.model.dropoff_dimensions.y.amplitudes,
            self.model.dropoff_dimensions.z.amplitudes,
        )
        if not np.isfinite([lower_threshold, upper_threshold]).all():
            raise ValueError("procedural mesh settings must be finite")
        if lower_threshold > upper_threshold:
            raise ValueError("lower_threshold must not exceed upper_threshold")
        return {
            "dimensions": dimensions,
            "transform": transform_prepared,
            "lower_threshold": lower_threshold,
            "upper_threshold": upper_threshold,
            "amplitudes": amplitudes,
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
        grid_data = self._apply_dropoff(grid_data, prepared["amplitudes"])
        selected = (grid_data >= prepared["lower_threshold"]) & (
            grid_data <= prepared["upper_threshold"]
        )
        grid_data = np.where(selected, grid_data, 0.0)

        mesh = self._build_surface_mesh(grid_data)
        self.grid_data = grid_data
        report(1.0)
        return {"grid_data": grid_data, "mesh_data": mesh}

    def interpolate_symmetric_amplitudes(
        self,
        amplitudes,
        sample_count: int,
    ) -> np.ndarray:
        amplitudes = np.asarray(amplitudes, dtype=float)

        if len(amplitudes) == 0:
            return np.ones(sample_count)

        half_positions = np.linspace(0.0, 1.0, len(amplitudes))
        positions = np.linspace(-1.0, 1.0, sample_count)

        distance = np.abs(positions)

        return np.interp(
            distance,
            half_positions,
            amplitudes,
        )

    def interpolate_amplitudes(
        self,
        amplitudes: tuple[np.ndarray, np.ndarray, np.ndarray],
        grid_dimensions: tuple[int, int, int],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Interpolate the amplitudes for each dimension based on the sample count."""
        x_amplitudes = self.interpolate_symmetric_amplitudes(
            amplitudes[0],
            grid_dimensions[0],
        )

        y_amplitudes = self.interpolate_symmetric_amplitudes(
            amplitudes[1],
            grid_dimensions[1],
        )

        z_amplitudes = self.interpolate_symmetric_amplitudes(
            amplitudes[2],
            grid_dimensions[2],
        )
        return x_amplitudes, y_amplitudes, z_amplitudes

    def _apply_dropoff(self, grid_data, amplitudes):
        if amplitudes is None:
            return grid_data
        interpolated_amplitudes = self.interpolate_amplitudes(
            amplitudes,
            grid_data.shape,
        )
        x_amp, y_amp, z_amp = interpolated_amplitudes

        grid_data *= x_amp[:, None, None] * y_amp[None, :, None] * z_amp[None, None, :]
        return grid_data

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
