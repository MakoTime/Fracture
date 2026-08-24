from PySide6.QtWidgets import QWidget

from .model import MeshEditModel
from .view import MeshEditView


def create_mesh_edit_dialog(
    mesh_object,
    colourmaps=(),
    parent: QWidget | None = None,
    deduper=None,
) -> MeshEditView:
    """Build a dialog for editing an existing mesh."""
    deduper = deduper or (lambda name: name)
    return MeshEditView(
        MeshEditModel.from_mesh_object(mesh_object),
        colourmaps=colourmaps,
        parent=parent,
        deduper=deduper,
    )
