import numpy as np
import pyvista as pv


def _rotation_matrix(dip, azimuth):
    dip_radians = np.deg2rad(float(dip))
    azimuth_radians = np.deg2rad(float(azimuth))
    dip_rotation = np.array(
        [
            [np.cos(dip_radians), 0.0, np.sin(dip_radians)],
            [0.0, 1.0, 0.0],
            [-np.sin(dip_radians), 0.0, np.cos(dip_radians)],
        ]
    )
    azimuth_rotation = np.array(
        [
            [np.cos(azimuth_radians), -np.sin(azimuth_radians), 0.0],
            [np.sin(azimuth_radians), np.cos(azimuth_radians), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return azimuth_rotation @ dip_rotation


def _orbit_frame(orbit_normal, orbit_angle):
    """Return radial, tangent, and local-up vectors for an orbit position."""
    reference_axis = np.array((0.0, 1.0, 0.0))
    if abs(np.dot(orbit_normal, reference_axis)) > 0.99:
        reference_axis = np.array((1.0, 0.0, 0.0))
    reference_direction = np.cross(reference_axis, orbit_normal)
    reference_direction /= np.linalg.norm(reference_direction)
    tangent_direction = np.cross(orbit_normal, reference_direction)
    angle_radians = np.deg2rad(float(orbit_angle))
    radial_direction = (
        np.cos(angle_radians) * reference_direction
        + np.sin(angle_radians) * tangent_direction
    )
    tangent_direction = (
        -np.sin(angle_radians) * reference_direction
        + np.cos(angle_radians) * tangent_direction
    )
    local_up = np.cross(radial_direction, tangent_direction)
    return radial_direction, tangent_direction, local_up


def build_island_mesh(prepared, base_reference_time=None):
    """Copy and orient a source mesh at the requested simulation time."""
    source = prepared["mesh_data"]
    if source is None or not hasattr(source, "copy"):
        raise ValueError("Island source mesh must be renderable mesh data")
    mesh = source.copy(deep=True)
    if not isinstance(mesh, pv.DataSet):
        raise TypeError("Island source mesh must be a PyVista dataset")
    centre = np.asarray(prepared["centre"], dtype=float)
    if centre.shape != (3,) or not np.isfinite(centre).all():
        raise ValueError("Island centre must contain three finite values")
    radius = float(prepared["core_offset"])
    if radius < 0.0 or not np.isfinite(radius):
        raise ValueError("Island core_offset must be a finite non-negative radius")
    orbit_normal = np.asarray(
        prepared.get("orbit_normal", (0.0, 0.0, 1.0)), dtype=float
    )
    if orbit_normal.shape != (3,) or not np.isfinite(orbit_normal).all():
        raise ValueError("Island orbit normal must contain three finite values")
    normal_length = np.linalg.norm(orbit_normal)
    if normal_length <= 1e-12:
        raise ValueError("Island orbit normal must not be zero")
    orbit_normal /= normal_length

    orbit_angle = float(prepared.get("orbit_angle", 0.0)) + float(
        prepared.get("orbit_phase", 0.0)
    )
    if base_reference_time is None:
        base_reference_time = prepared["reference_time"]
    elapsed_seconds = (
        base_reference_time - prepared["reference_time"]
    ).total_seconds()
    orbit_angle += float(prepared.get("orbit_speed", 0.0)) * elapsed_seconds

    radial_direction, tangent_direction, local_up = _orbit_frame(
        orbit_normal, orbit_angle
    )
    current_position = centre + radius * radial_direction
    mesh.translate(-np.asarray(mesh.center), inplace=True)
    if prepared.get("curve_mesh", False) and radius > 1e-12:
        local_points = np.asarray(mesh.points).copy()
        tangent_angle = local_points[:, 0] / radius
        up_angle = local_points[:, 1] / radius
        arc_radius = radius + local_points[:, 2]
        curved_points = np.empty_like(local_points)
        curved_points[:, 0] = arc_radius * np.sin(tangent_angle) * np.cos(up_angle)
        curved_points[:, 1] = arc_radius * np.sin(up_angle)
        curved_points[:, 2] = (
            arc_radius * np.cos(tangent_angle) * np.cos(up_angle) - radius
        )
        mesh.points = curved_points
    rotation = np.column_stack((tangent_direction, local_up, radial_direction))
    mesh.points = np.asarray(mesh.points) @ rotation.T
    mesh.translate(current_position, inplace=True)
    return mesh



class IslandTask:
    """Build an island mesh from its source mesh and world configuration."""

    def __init__(self, block_object):
        self.block_object = block_object

    def prepare(self):
        return self.block_object.prepare()

    def process(self, prepared, progress_callback=None):
        return self.block_object.process(prepared, progress_callback)

    def execute(self, prepared, progress_callback=None):
        result = self.process(prepared, progress_callback)
        return self.block_object.commit(result)
