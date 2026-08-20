from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import MeshImportModel
from .view import ElevationImportView, MeshImportView


def create_mesh_import_dialog(
    model: Optional[MeshImportModel] = None,
    parent: Optional[QWidget] = None,
) -> MeshImportView:
    """Build a mesh import dialog from optional initial data."""
    return MeshImportView(model or MeshImportModel(), parent=parent)


def create_elevation_import_dialog(
    model: Optional[MeshImportModel] = None,
    parent: Optional[QWidget] = None,
) -> ElevationImportView:
    """Build a dialog for importing image elevation data."""
    return ElevationImportView(model or MeshImportModel(), parent=parent)
