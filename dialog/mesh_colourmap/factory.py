from PySide6.QtWidgets import QWidget

from .model import MeshColourmapModel
from .view import MeshColourmapView


def create_mesh_colourmap_dialog(
    model: MeshColourmapModel,
    colourmaps=(),
    parent: QWidget | None = None,
    on_apply=None,
) -> MeshColourmapView:
    return MeshColourmapView(
        model,
        colourmaps=colourmaps,
        parent=parent,
        on_apply=on_apply,
    )
