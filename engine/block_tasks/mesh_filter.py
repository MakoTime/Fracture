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
        block_object=None,
    ):
        self.source_block = source_block
        self.transform_block = transform_block
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.block_object = block_object
        self.grid_data = None
        self.mesh_data = None

    def prepare(self):
        return {
            "minimum": self.minimum,
            "maximum": self.maximum,
            "penetration": max(1, int(self.transform_block.penetration)),
            "application_mode": getattr(
                self.transform_block, "application_mode", "voxel_remesh"
            ),
            "transform": self.transform_block.prepare(),
        }

    def process(self, prepared, progress_callback=None):
        return self.execute(prepared, progress_callback)

    def execute(self, prepared, progress_callback=None):
        report = progress_callback or (lambda progress: None)
        report(0.0)
        values = self._filtered_grid_data(prepared)
        isovalue = max(prepared["minimum"], prepared["maximum"])
        mesh_data = self._surface_mesh(values, isovalue)
        self.grid_data = values
        self.mesh_data = mesh_data
        if self.block_object is not None:
            self.block_object.set_mesh_data(mesh_data)
            self.block_object.commit()
        report(1.0)
        return self.block_object if self.block_object is not None else self

    def _filtered_grid_data(self, prepared):
        values = np.asarray(self.source_block.grid_data, dtype=float).copy()
        if values.ndim != 3:
            raise ValueError("source grid data must be three-dimensional")
        if not np.isfinite(values).all():
            raise ValueError("source grid data must contain only finite values")
        if self.transform_block is None or not hasattr(
            self.transform_block, "noise_field"
        ):
            raise ValueError("a filter transform is required")
        active = values != 0.0
        noise = self.transform_block._build_noise_field(
            values.shape,
            prepared["transform"],
        )
        contour_level = max(prepared["minimum"], prepared["maximum"])
        if prepared["application_mode"] == "noise_mask":
            minimum = min(prepared["minimum"], prepared["maximum"])
            maximum = max(prepared["minimum"], prepared["maximum"])
            values[active & ((noise < minimum) | (noise > maximum))] = 0.0
            return values
        if prepared["application_mode"] == "surface_displacement":
            active = values >= contour_level
            distance = self._signed_surface_distance(
                active,
                prepared["penetration"],
            )
            affected = distance != 0
            values[affected] = contour_level + (
                distance[affected] / prepared["penetration"]
                - (noise[affected] - 0.5)
            )
            return values
        distance = self._surface_distance(active, prepared["penetration"])
        affected = distance >= 0
        values[affected] = contour_level + (
            distance[affected] / prepared["penetration"] - (noise[affected] - 0.5)
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

    @classmethod
    def _signed_surface_distance(cls, active, penetration):
        active = np.asarray(active, dtype=bool)
        inside = cls._surface_distance(active, penetration)
        outside = cls._surface_distance(~active, penetration)
        distance = np.zeros(active.shape, dtype=float)
        distance[inside >= 0] = inside[inside >= 0] + 0.5
        distance[outside >= 0] = -(outside[outside >= 0] + 0.5)
        return distance

    @staticmethod
    def _surface_mesh(values, isovalue):
        if isovalue < values.min() or isovalue > values.max():
            return pv.PolyData()
        image = pv.ImageData(dimensions=values.shape, spacing=(1.0, 1.0, 1.0))
        image.point_data["values"] = values.ravel(order="F")
        return image.contour(isosurfaces=[isovalue], scalars="values")
