from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import WorldConfigModel
from .view import WorldConfigView


def create_world_config_dialog(world_config, parent: Optional[QWidget] = None):
    """Build the world configuration editor."""
    return WorldConfigView(WorldConfigModel.from_object(world_config), parent=parent)