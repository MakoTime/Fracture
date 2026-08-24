from dataclasses import dataclass

import numpy as np
import pyvista as pv

from engine.block_objects import ColourmapBlockObject, PerlinNoiseTransformBlockObject
from objects.mesh_object import MeshObject


@dataclass
class MeshColourmapModel:
    mesh_object: MeshObject | None = None
    colourmap: object | None = None
    field1_source: str = "elevation"
    field2_source: str = "normal_z"
    invert_field1: bool = False
    invert_field2: bool = False
    scope: str = "local"

    SOURCES = (
        ("elevation", "Relative elevation"),
        ("normal_z", "Inverted surface normal Z"),
    )

    @staticmethod
    def _copy_colourmap(colourmap):
        if colourmap is None:
            return None
        transform = colourmap.perlin_noise_transform
        copied_transform = None
        if transform is not None:
            copied_transform = PerlinNoiseTransformBlockObject(
                name=transform.name,
                comments=transform.comments,
                frequencies=transform.frequencies,
                amplitudes=transform.amplitudes,
                seed=transform.seed,
                curve_mode=transform.curve_mode,
                curve_points=transform.curve_points,
                curve_handles=transform.curve_handles,
                frequency_start=transform.frequency_start,
                frequency_end=transform.frequency_end,
                sample_count=transform.sample_count,
                manual_sampling=transform.manual_sampling,
                preset=transform.preset,
                preset_options=dict(transform.preset_options),
            )
        return ColourmapBlockObject(
            stops=colourmap.stops,
            name=colourmap.name,
            field1_name=colourmap.field1_name,
            field2_name=colourmap.field2_name,
            field1_positions=colourmap.field1_positions,
            field2_positions=colourmap.field2_positions,
            colour_grid=colourmap.colour_grid,
            field1_curve_points=colourmap.field1_curve_points,
            field1_curve_handles=colourmap.field1_curve_handles,
            field2_curve_points=colourmap.field2_curve_points,
            field2_curve_handles=colourmap.field2_curve_handles,
            comments=colourmap.comments,
            perlin_noise_transform=copied_transform,
            noise_enabled=colourmap.noise_enabled,
        )

    @classmethod
    def from_mesh_object(cls, mesh_object):
        selected = mesh_object.colourmap
        return cls(
            mesh_object=mesh_object,
            colourmap=selected,
            field1_source=mesh_object.colourmap_field_sources[0],
            field2_source=mesh_object.colourmap_field_sources[1],
            invert_field1=mesh_object.colourmap_field_inversions[0],
            invert_field2=mesh_object.colourmap_field_inversions[1],
            scope=getattr(mesh_object.block_object, "colourmap_scope", "local"),
        )

    def preview_data(self):
        if self.mesh_object is None or self.mesh_object.mesh_data is None:
            return None
        payload = self.mesh_object.mesh_data.copy(deep=True)
        if isinstance(payload, pv.StructuredGrid):
            payload = payload.extract_surface(
                algorithm="dataset_surface",
            ).compute_normals(
                auto_orient_normals=True,
                split_vertices=False,
                inplace=False,
            )
        elif (
            hasattr(payload, "compute_normals") and "Normals" not in payload.point_data
        ):
            payload = payload.compute_normals(
                auto_orient_normals=True,
                split_vertices=False,
                inplace=False,
            )

        colourmap = getattr(self.colourmap, "block_object", self.colourmap)
        if colourmap is None or not hasattr(payload, "points"):
            return payload

        points = np.asarray(payload.points)
        elevation = points[:, 2]
        elevation_span = (
            float(elevation.max() - elevation.min()) if len(elevation) else 0.0
        )
        relative_elevation = (
            np.zeros_like(elevation)
            if elevation_span <= 1e-12
            else (elevation - elevation.min()) / elevation_span
        )
        normals = np.asarray(payload.point_data.get("Normals", np.zeros_like(points)))
        normal_z = np.clip((1.0 - normals[:, 2]) * 0.5, 0.0, 1.0)
        field_values = {
            "elevation": relative_elevation,
            "normal_z": normal_z,
        }
        first_field = field_values.get(self.field1_source, relative_elevation)
        second_field = field_values.get(self.field2_source, normal_z)
        if self.invert_field1:
            first_field = 1.0 - first_field
        if self.invert_field2:
            second_field = 1.0 - second_field
        copied_colourmap = self._copy_colourmap(colourmap)
        payload.point_data["__colourmap_rgba"] = np.clip(
            np.round(copied_colourmap.apply_fields(first_field, second_field) * 255.0),
            0,
            255,
        ).astype(np.uint8)
        return payload

    def apply(self, mesh_object):
        mesh_object.set_colourmap(self.colourmap)
        mesh_object.set_colourmap_field_sources(
            self.field1_source,
            self.field2_source,
        )
        mesh_object.set_colourmap_data_options(
            self.invert_field1,
            self.invert_field2,
        )
        mesh_object.set_colourmap_scope(self.scope)
        return mesh_object
