from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import MeshEditModel
from .view import MeshEditView


def create_mesh_edit_dialog(
    mesh_object,
    parent: Optional[QWidget] = None,
) -> MeshEditView:
    """Build a dialog for editing an existing mesh."""
    return MeshEditView(MeshEditModel.from_mesh_object(mesh_object), parent=parent)