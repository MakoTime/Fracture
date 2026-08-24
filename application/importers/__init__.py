from .object_importer import ObjectImporterModel
from .registry import ImportBindingRegistry, register_import_binding

__all__ = [
    "ColourmapController",
    "ImportBindingRegistry",
    "MeshImportController",
    "ObjectImporterModel",
    "TransformController",
    "WorldConfigController",
    "register_import_binding",
]


def __getattr__(name):
    if name == "ColourmapController":
        from .colourmap_controller import ColourmapController

        return ColourmapController
    if name == "MeshImportController":
        from .mesh_controller import MeshImportController

        return MeshImportController
    if name == "TransformController":
        from .transform_controller import TransformController

        return TransformController
    if name == "WorldConfigController":
        from .world_config_controller import WorldConfigController

        return WorldConfigController
    raise AttributeError(name)
