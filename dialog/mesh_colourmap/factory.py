from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import MeshColourmapModel
from .view import MeshColourmapView


def create_mesh_colourmap_dialog(
    model: MeshColourmapModel,
    colourmaps=(),
    parent: Optional[QWidget] = None,
) -> MeshColourmapView:
    return MeshColourmapView(model, colourmaps=colourmaps, parent=parent)
