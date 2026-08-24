from PySide6.QtWidgets import QWidget

from .model import IslandModel
from .view import IslandView


def create_island_dialog(
    island,
    parent: QWidget | None = None,
    on_apply=None,
    source_meshes=(),
    new_island=False,
    deduper=None,
):
    deduper = deduper or (lambda name: name)
    model = IslandModel.from_island(island)
    model.set_source_meshes(source_meshes)
    if new_island and model.source_mesh is not None:
        model.name = f"{model.source_mesh.name} island"
    return IslandView(
        model,
        parent=parent,
        on_apply=on_apply,
        deduper=deduper,
    )
