"""Global root nodes owned by the tree component."""

from .mesh import mesh_root
from .colourmaps import colourmap_root
from .transforms import transform_root
from .root_objects import root_objects

__all__ = ["colourmap_root", "mesh_root", "root_objects", "transform_root"]