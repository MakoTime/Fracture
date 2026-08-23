import numpy as np
import pyvista as pv

from engine.block_objects import GeneratedMeshBlockObject
from engine.block_objects import PerlinNoiseTransformBlockObject


class MeshGenerateTask:
    """Build a mesh block from a generated scalar grid field."""

    def __init__(self, model, block_object=None):
        self.model = model
        self.grid_data = None
        self.block_object = block_object or GeneratedMeshBlockObject(
            name=model.name.strip() or "Generated Mesh",
            guid=model.guid,
            perlin_noise_transform=self._perlin_noise_block(),
            noise_enabled=model.noise_enabled,
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
        return {
            "dimensions": tuple(max(1, int(value)) for value in self.model.grid_size),
            "transform": None if transform is None else transform.prepare(),
        }

    def process(self, prepared, progress_callback=None):
        return self.execute(prepared, progress_callback)

    def execute(self, prepared, progress_callback=None):
        report = progress_callback or (lambda progress: None)
        report(0.0)
        dimensions = prepared["dimensions"]
        base_grid_data = self._build_grid_data(
            dimensions,
            apply_noise=False,
            transform_prepared=prepared["transform"],
        )
        self.grid_data = self._build_grid_data(
            dimensions,
            transform_prepared=prepared["transform"],
        )
        self.block_object.set_grid_data(self.grid_data)
        self.block_object.noise_enabled = self._noise_is_active()
        report(0.35)
        isovalues = self._contour_levels()
        self.block_object.set_mesh_data(self._build_surface_mesh(
            self.grid_data,
            isovalue=isovalues,
        ))
        if self._noise_is_active() and getattr(
            self.model, "show_mask_surface", True
        ):
            self.block_object.set_mask_mesh_data(self._build_surface_mesh(
                base_grid_data,
                isovalue=self._mask_contour_level(),
            ))
        self.block_object.commit()
        report(1.0)
        return self.block_object

    def _build_grid_data(
        self,
        dimensions,
        apply_noise=True,
        transform_prepared=None,
    ):
        """Build the field, then apply masks as a final boolean AND."""
        source_grid_data = getattr(self.model, "source_grid_data", None)
        if source_grid_data is not None:
            field = np.asarray(source_grid_data, dtype=float).copy()
            if field.shape != dimensions:
                raise ValueError("source grid data shape must match grid size")
        else:
            field = np.ones(dimensions, dtype=float)

        active_mask = self._build_active_mask(dimensions)
        surface_mask = active_mask
        if source_grid_data is not None:
            surface_mask = active_mask & (field != 0.0)
        if apply_noise and self._noise_is_active():
            transform = self.block_object.perlin_noise_transform
            noise = transform._build_noise_field(
                dimensions,
                transform_prepared,
            )
            penetration = max(1, int(self.model.noise_penetration))
            contour_level = self._contour_levels()[0]
            if self.model.flexible_masks:
                signed_distance = self._build_signed_surface_distance(
                    surface_mask,
                    penetration,
                )
                affected = signed_distance != 0
                displacement = noise[affected] - 0.5
                displaced_field = contour_level + (
                    signed_distance[affected] / penetration
                    - displacement
                )
                field[affected] = displaced_field
            else:
                surface_distance = self._build_surface_distance(
                    surface_mask,
                    penetration,
                )
                affected = surface_distance >= 0
                displacement = noise[affected] - 0.5
                displaced_field = contour_level + (
                    surface_distance[affected] / penetration
                    - displacement
                )
                field[affected] = displaced_field

        if not self.model.flexible_masks:
            field *= active_mask
        return field

    def _build_active_mask(self, dimensions):
        active_mask = np.ones(dimensions, dtype=bool)
        masks = (
            (self.model.x_mask, (None, slice(None), slice(None))),
            (self.model.y_mask, (slice(None), None, slice(None))),
            (self.model.z_mask, (slice(None), slice(None), None)),
        )
        for mask, placement in masks:
            if mask is None:
                continue
            values = np.asarray(mask, dtype=bool)
            active_mask &= values[placement]
        return active_mask

    def _contour_levels(self):
        if not self._noise_is_active():
            return (0.5,)
        minimum = float(self.model.noise_minimum)
        maximum = float(self.model.noise_maximum)
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        del minimum
        return (maximum,)

    def _noise_is_active(self):
        return bool(
            self.model.noise_enabled
            and self.block_object.perlin_noise_transform is not None
        )

    def _mask_contour_level(self):
        minimum = float(self.model.noise_minimum)
        maximum = float(self.model.noise_maximum)
        return min(minimum, maximum)

    @staticmethod
    def _build_surface_layers(active_mask, penetration):
        return MeshGenerateTask._build_surface_distance(
            active_mask,
            penetration,
        ) >= 0

    @staticmethod
    def _build_signed_surface_distance(active_mask, penetration):
        active_mask = np.asarray(active_mask, dtype=bool)
        active_distance = MeshGenerateTask._build_surface_distance(
            active_mask,
            penetration,
        )
        inactive_distance = MeshGenerateTask._build_surface_distance(
            ~active_mask,
            penetration,
        )
        signed_distance = np.zeros(active_mask.shape, dtype=float)
        active_affected = active_distance >= 0
        inactive_affected = inactive_distance >= 0
        signed_distance[active_affected] = active_distance[active_affected] + 0.5
        signed_distance[inactive_affected] = -(
            inactive_distance[inactive_affected] + 0.5
        )
        return signed_distance

    @staticmethod
    def _build_surface_distance(active_mask, penetration):
        active_mask = np.asarray(active_mask, dtype=bool)
        if active_mask.ndim != 3:
            raise ValueError("active_mask must be a three-dimensional array")
        penetration = max(1, int(penetration))
        distance = np.full(active_mask.shape, -1, dtype=int)
        surface = np.zeros_like(active_mask)
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
                    active_mask[tuple(source)]
                    & ~active_mask[tuple(neighbor)]
                )
            distance[surface] = 0
        frontier = surface
        for layer_index in range(1, penetration):
            expanded = np.zeros_like(active_mask)
            padded_frontier = np.pad(frontier, 1, constant_values=False)
            expanded |= padded_frontier[:-2, 1:-1, 1:-1]
            expanded |= padded_frontier[2:, 1:-1, 1:-1]
            expanded |= padded_frontier[1:-1, :-2, 1:-1]
            expanded |= padded_frontier[1:-1, 2:, 1:-1]
            expanded |= padded_frontier[1:-1, 1:-1, :-2]
            expanded |= padded_frontier[1:-1, 1:-1, 2:]
            frontier = expanded & active_mask & (distance < 0)
            distance[frontier] = layer_index
        return distance

    @staticmethod
    def _build_surface_mesh(grid_data, isovalue):
        values = np.asarray(grid_data, dtype=float)
        if values.ndim != 3:
            raise ValueError("grid_data must be a three-dimensional scalar field")
        if not np.isfinite(values).all():
            raise ValueError("grid_data must contain only finite values")
        isovalues = np.atleast_1d(isovalue).astype(float)
        if not np.isfinite(isovalues).all():
            raise ValueError("isovalue must contain only finite values")
        if np.any(isovalues < values.min()) or np.any(isovalues > values.max()):
            return pv.PolyData()
        # Pad below the isovalue so a solid region touching the grid edge is
        # capped instead of leaving the isosurface open there.
        padded = np.pad(values, 1, constant_values=values.min())
        image = pv.ImageData(
            dimensions=padded.shape,
            spacing=(1.0, 1.0, 1.0),
        )
        image.point_data["values"] = padded.ravel(order="F")
        contour = image.contour(isosurfaces=isovalues.tolist(), scalars="values")
        contour.translate((-1.0, -1.0, -1.0), inplace=True)
        return contour
