import numpy as np
import pyvista as pv


class MeshFilterTask:
    """Apply a transform to a source grid and write only to a filter block."""

    def __init__(
        self,
        source_block,
        transform_block,
        minimum,
        maximum,
        penetration,
        block_object=None,
    ):
        self.source_block = source_block
        self.transform_block = transform_block
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.penetration = max(1, int(penetration))
        self.block_object = block_object
        self.grid_data = None
        self.mesh_data = None

    def process(self, progress_callback=None):
        report = progress_callback or (lambda progress: None)
        report(0.0)
        values = self._filtered_grid_data()
        isovalue = max(self.minimum, self.maximum)
        mesh_data = self._surface_mesh(values, isovalue)
        self.grid_data = values
        self.mesh_data = mesh_data
        if self.block_object is not None:
            self.block_object.set_mesh_data(mesh_data)
            self.block_object.process()
        report(1.0)
        return self.block_object if self.block_object is not None else self

    def _filtered_grid_data(self):
        values = np.asarray(self.source_block.grid_data, dtype=float).copy()
        if values.ndim != 3:
            raise ValueError("source grid data must be three-dimensional")
        if not np.isfinite(values).all():
            raise ValueError("source grid data must contain only finite values")
        if self.transform_block is None or not hasattr(
            self.transform_block, "noise_field"
        ):
            raise ValueError("a filter transform is required")
        self.transform_block.prepare()
        self.transform_block.process()

        active = values != 0.0
        distance = self._surface_distance(active, self.penetration)
        affected = distance >= 0
        noise = self.transform_block.noise_field(values.shape)
        contour_level = max(self.minimum, self.maximum)
        values[affected] = contour_level + (
            distance[affected] / self.penetration - (noise[affected] - 0.5)
        )
        return values

    @staticmethod
    def _surface_distance(active, penetration):
        active = np.asarray(active, dtype=bool)
        distance = np.full(active.shape, -1, dtype=int)
        surface = np.zeros_like(active)
        for axis in range(3):
            for direction in (-1, 1):
                source = [slice(None)] * 3
                neighbor = [slice(None)] * 3
                if direction < 0:
                    source[axis] = slice(1, None)
                    neighbor[axis] = slice(None, -1)
                else:
                    source[axis] = slice(None, -1)
                    neighbor[axis] = slice(1, None)
                surface[tuple(source)] |= (
                    active[tuple(source)] & ~active[tuple(neighbor)]
                )
        distance[surface] = 0
        frontier = surface
        for layer in range(1, penetration):
            expanded = np.zeros_like(active)
            padded = np.pad(frontier, 1, constant_values=False)
            expanded |= padded[:-2, 1:-1, 1:-1]
            expanded |= padded[2:, 1:-1, 1:-1]
            expanded |= padded[1:-1, :-2, 1:-1]
            expanded |= padded[1:-1, 2:, 1:-1]
            expanded |= padded[1:-1, 1:-1, :-2]
            expanded |= padded[1:-1, 1:-1, 2:]
            frontier = expanded & active & (distance < 0)
            distance[frontier] = layer
        return distance

    @staticmethod
    def _surface_mesh(values, isovalue):
        if isovalue < values.min() or isovalue > values.max():
            return pv.PolyData()
        image = pv.ImageData(dimensions=values.shape, spacing=(1.0, 1.0, 1.0))
        image.point_data["values"] = values.ravel(order="F")
        return image.contour(isosurfaces=[isovalue], scalars="values")
