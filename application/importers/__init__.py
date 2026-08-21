from .registry import ImportBindingRegistry, register_import_binding
from .object_importer import ObjectImporterModel

__all__ = [
    "ImportBindingRegistry",
    "MeshImportController",
    "ColourmapController",
    "ObjectImporterModel",
    "TransformController",
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
    raise AttributeError(name)
