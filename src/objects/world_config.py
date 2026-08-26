from PySide6.QtGui import QIcon

from src.common.icons import get_icon
from src.common.calendar import WorldClock, WorldTime
from src.engine.block_objects import WorldConfigBlockObject
from src.engine.block_objects.world_config import SavedTimes, WorldStateBlockObject

from .object_base import ObjectBase


class WorldStateObject(ObjectBase):
    """The singleton project object containing world state information."""

    def __init__(
        self,
        name: str = "World State",
        block_object: WorldStateBlockObject | None = None,
        icon: QIcon | None = None,
        guid: str | None = None,
        auto_register_root: bool = False,
    ):
        block = block_object or WorldStateBlockObject(name=name, guid=guid)
        if not isinstance(block, WorldStateBlockObject):
            raise TypeError("WorldState requires a WorldStateBlockObject")
        self.world_state_block_object = block
        self._ready_callback = None
        super().__init__(
            name=block.name,
            icon=icon if icon is not None else get_icon("clock"),
            guid=block.guid,
            auto_register_root=auto_register_root,
            register_in_tree=False,
        )
        self._date_time = block.date_time
        self._saved_times = block.saved_times

    def time_updated(self):
        """Update the world state time and emit a signal."""
        self.world_state_block_object.invalidate()

    def set_ready_callback(self, callback):
        """Set the callback to be called when the world state is ready."""
        self._ready_callback = callback

    def deserialise_to_block(self, data: dict):
        """Update the block object from a serialised dictionary."""
        self.world_state_block_object.update_configuration(
            name=data.get("name", None),
            date_time=data.get("date_time", None),
            saved_times=data.get("saved_times", None),
        )
        self.date_time = self.world_state_block_object.date_time
        self.saved_times = self.world_state_block_object.saved_times
        if self._ready_callback is not None:
            self._ready_callback()

    def serialise_from_block(self) -> dict:
        """Serialise the block object to a dictionary."""
        self.load_to_block()
        return self.world_state_block_object.to_json()

    def load_to_block(self):
        self.world_state_block_object.date_time = self.date_time
        self.world_state_block_object.saved_times = self.saved_times
        self.world_state_block_object.invalidate()

    def clear(self):
        self.date_time = WorldTime.now()
        self.saved_times = SavedTimes()
        self.world_state_block_object.saved_times.rows.clear()
        self.world_state_block_object.date_time = WorldTime.now()
        self.world_state_block_object.invalidate()

    @property
    def block_object(self):
        return self.world_state_block_object

    @property
    def date_time(self):
        return self._date_time

    @date_time.setter
    def date_time(self, value: WorldTime):
        self._date_time = value
        WorldClock.set(value)

    @property
    def saved_times(self):
        return self._saved_times

    @saved_times.setter
    def saved_times(self, value: SavedTimes):
        self._saved_times = value
        self.world_state_block_object.saved_times = value




class WorldConfig(ObjectBase):
    """The singleton project object containing world configuration."""

    def __init__(
        self,
        name: str = "World Config",
        block_object: WorldConfigBlockObject | None = None,
        icon: QIcon | None = None,
        guid: str | None = None,
        auto_register_root: bool = False,
    ):
        block = block_object or WorldConfigBlockObject(name=name, guid=guid)
        if not isinstance(block, WorldConfigBlockObject):
            raise TypeError("WorldConfig requires a WorldConfigBlockObject")
        self.world_config_block_object = block
        super().__init__(
            name=block.name,
            icon=icon if icon is not None else get_icon("earth"),
            guid=block.guid,
            auto_register_root=auto_register_root,
        )

    @property
    def block_object(self):
        return self.world_config_block_object

    @property
    def name(self):
        return (
            self.world_config_block_object.name
            if hasattr(self, "world_config_block_object")
            else self._name
        )

    @name.setter
    def name(self, value):
        self._name = value
        if hasattr(self, "world_config_block_object"):
            self.world_config_block_object.name = value

    @property
    def centre(self):
        return self.world_config_block_object.centre

    def update_configuration(self, *, name=None, centre=None):
        result = self.block_object.update_configuration(name=name, centre=centre)
        self.node.name = self.name
        if hasattr(self, "row_data"):
            self.row_data.name = self.name
        return result
