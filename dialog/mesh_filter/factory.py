from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import MeshFilterModel
from .view import MeshFilterView


def create_mesh_filter_dialog(
    model: MeshFilterModel,
    parent: Optional[QWidget] = None,
    on_apply=None,
    transforms=(),
    deduper=None,
) -> MeshFilterView:
    deduper = deduper or (lambda name: name)
    return MeshFilterView(
        model,
        transforms=transforms,
        parent=parent,
        on_apply=on_apply,
        deduper=deduper,
    )
