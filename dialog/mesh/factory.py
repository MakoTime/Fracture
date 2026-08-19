from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import MeshImportModel
from .view import MeshImportView


def create_mesh_import_dialog(
    model: Optional[MeshImportModel] = None,
    parent: Optional[QWidget] = None,
) -> MeshImportView:
    """Build a mesh import dialog from optional initial data."""
    return MeshImportView(model or MeshImportModel(), parent=parent)
