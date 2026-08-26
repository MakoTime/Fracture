from PySide6.QtWidgets import QWidget

from src.components.world_state.model import WorldStateModel
from src.components.world_state.view import WorldStateView


def create_world_state_widget(
    world_config, parent: QWidget | None = None, deduper=None
):
    """Build the world state editor."""
    deduper = deduper or (lambda name: name)
    return WorldStateView(
        WorldStateModel.from_object(world_config), parent=parent, deduper=deduper
    )
