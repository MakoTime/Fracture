"""Global root nodes owned by the tree component."""

from .colourmaps import colourmap_root
from .islands import island_root
from .mesh import mesh_root
from .root_objects import root_objects
from .transforms import transform_root

_special_roots_loaded = False


def _load_special_roots():
    global _special_roots_loaded
    if _special_roots_loaded:
        return
    from .world_config_root import world_config

    root_objects.protect(world_config.node)
    root_objects.protect(island_root)
    globals()["world_config"] = world_config
    _special_roots_loaded = True


def __getattr__(name):
    if name == "world_config":
        _load_special_roots()
        return globals()[name]
    raise AttributeError(name)


__all__ = [
    "colourmap_root",
    "island_root",
    "mesh_root",
    "root_objects",
    "transform_root",
    "world_config",
]
