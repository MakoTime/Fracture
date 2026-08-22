from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import IslandModel
from .view import IslandView


def create_island_dialog(
    island,
    parent: Optional[QWidget] = None,
    on_apply=None,
    source_meshes=(),
):
    model = IslandModel.from_island(island)
    model.set_source_meshes(source_meshes)
    return IslandView(
        model,
        parent=parent,
        on_apply=on_apply,
    )