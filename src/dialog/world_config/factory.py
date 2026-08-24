from PySide6.QtWidgets import QWidget

from .model import WorldConfigModel
from .view import WorldConfigView


def create_world_config_dialog(
    world_config, parent: QWidget | None = None, deduper=None
):
    """Build the world configuration editor."""
    deduper = deduper or (lambda name: name)
    return WorldConfigView(
        WorldConfigModel.from_object(world_config), parent=parent, deduper=deduper
    )
