from PySide6.QtWidgets import QWidget

from .model import MeshImportModel
from .view import ElevationImportView, MeshImportView


def create_mesh_import_dialog(
    model: MeshImportModel | None = None,
    parent: QWidget | None = None,
    deduper=None,
) -> MeshImportView:
    """Build a mesh import dialog from optional initial data."""
    deduper = deduper or (lambda name: name)
    return MeshImportView(model or MeshImportModel(), parent=parent, deduper=deduper)


def create_elevation_import_dialog(
    model: MeshImportModel | None = None,
    parent: QWidget | None = None,
    deduper=None,
) -> ElevationImportView:
    """Build a dialog for importing image elevation data."""
    deduper = deduper or (lambda name: name)
    return ElevationImportView(
        model or MeshImportModel(), parent=parent, deduper=deduper
    )
