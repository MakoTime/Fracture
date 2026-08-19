from .registry import ImportBindingRegistry, register_import_binding
from .object_importer import ObjectImporterModel

__all__ = [
    "ImportBindingRegistry",
    "MeshImportController",
    "ObjectImporterModel",
    "register_import_binding",
]


def __getattr__(name):
    if name == "MeshImportController":
        from .mesh_controller import MeshImportController

        return MeshImportController
    raise AttributeError(name)
