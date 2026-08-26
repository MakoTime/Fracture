from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import (
    QAbstractItemModel,
    QAbstractTableModel,
    QModelIndex,
    Qt,
    Signal,
)

from src.common.calendar import WorldTime
from src.components.tree.roots import root_objects, world_config
from src.engine.block_objects.world_config import SavedTimes, DatetimeRow
from src.objects.world_config import WorldStateObject


class SavedTimesTableModel(QAbstractTableModel):
    """Table model for the saved times in the world configuration."""

    HEADER, DATE, TIME, ACTIVATE = range(4)

    time_set = Signal(WorldTime)

    def __init__(self, world_state_model: "WorldStateModel", parent=None):
        super().__init__(parent)
        self.world_state_model = world_state_model
        self.world_state_model.saved_times_changed.connect(
            self._world_state_saved_times_changed
        )

    @property
    def saved_time_count(self):
        return self.world_state_model.saved_time_count

    def saved_time_at(self, row):
        return self.world_state_model.saved_time_at(row)

    def _world_state_saved_times_changed(self):
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return self.saved_time_count + 1

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return 4

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if index.row() >= self.saved_time_count:
            if role == Qt.DisplayRole and index.column() == self.ACTIVATE:
                return "Go to"
            return None

        row = self.saved_time_at(index.row())

        if role == Qt.DisplayRole:
            if index.column() == self.HEADER:
                return row.name

            if index.column() == self.TIME:
                return self.format_time(row.date)

            if index.column() == self.ACTIVATE:
                return "Go to"

        return None

    @staticmethod
    def format_time(value: WorldTime) -> str:
        return f"{value.hours:02d}:{value.minutes:02d}:{value.seconds:02d}"

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            headers = {
                self.HEADER: "Name",
                self.DATE: "Date",
                self.TIME: "Time",
                self.ACTIVATE: "Go to",
            }
            return headers.get(section)

        return None

    def flags(self, index):
        flags = super().flags(index)
        if not index.isValid() or index.row() >= self.saved_time_count:
            return flags
        if index.column() in (self.HEADER, self.DATE):
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if (
            not index.isValid()
            or index.row() >= self.saved_time_count
            or role != Qt.ItemDataRole.EditRole
            or index.column() not in (self.HEADER, self.DATE)
        ):
            return False

        row = self.saved_time_at(index.row())
        if index.column() == self.HEADER:
            self.world_state_model.edit_saved_time(
                index.row(),
                str(value),
                row.date,
            )
        else:
            self.world_state_model.edit_saved_time(
                index.row(),
                row.name,
                value,
            )
        return True

    def handle_click(self, index):
        """Handle commands represented by table columns."""
        if (
            index.isValid()
            and index.column() == self.ACTIVATE
            and index.row() < self.saved_time_count
        ):
            self.time_set.emit(self.saved_time_at(index.row()).date)

    def add_row(self, name, date_time):
        """Add a new saved time."""
        self.world_state_model.add_saved_time(name, date_time)

    def remove_row(self, row):
        """Remove a saved time."""
        self.world_state_model.remove_saved_time(row)

    def edit_row(self, row, name, date_time):
        """Edit an existing saved time."""
        self.world_state_model.edit_saved_time(row, name, date_time)

    def update_row_time(self, row, date_time):
        """Replace an existing saved time without changing its name."""
        saved_time = self.saved_time_at(row)
        self.world_state_model.edit_saved_time(row, saved_time.name, date_time)


@dataclass
class WorldStateModel(QAbstractItemModel):
    _world_state_object: WorldStateObject = field(
        default_factory=WorldStateObject,
        repr=False,
    )

    world_state_changed = Signal()
    saved_times_changed = Signal()
    time_changed = Signal(datetime)

    def __init__(
        self,
        world_state_object: WorldStateObject | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._world_state_object = (
            world_state_object if world_state_object is not None else WorldStateObject()
        )

    @property
    def world_state_object(self) -> WorldStateObject:
        return self._world_state_object

    @world_state_object.setter
    def world_state_object(self, value: WorldStateObject):
        self._world_state_object = value

        self.world_state_changed.emit()
        self.time_changed.emit(value.date_time)

    @property
    def date_time(self) -> WorldTime:
        return self._world_state_object.date_time

    @date_time.setter
    def date_time(self, value: WorldTime):
        if not isinstance(value, WorldTime):
            raise TypeError("date_time must be a WorldTime instance")

        if value == self._world_state_object.date_time:
            return

        self._world_state_object.date_time = value

        self.time_changed.emit(value)
        self.world_state_changed.emit()

    @property
    def saved_times(self) -> SavedTimes:
        return self._world_state_object.saved_times

    @saved_times.setter
    def saved_times(self, value: SavedTimes):
        self._world_state_object.saved_times = value
        self.saved_times_changed.emit()
        self.world_state_changed.emit()
        self.world_state_object.time_updated()

    @property
    def saved_time_count(self):
        return len(self.saved_times.rows)

    def saved_time_at(self, row):
        if not 0 <= row < self.saved_time_count:
            raise IndexError(row)
        return self.saved_times.rows[row]

    def add_saved_time(self, name, date_time):
        self.saved_times.rows.append(DatetimeRow(name=name, date=date_time))
        self.saved_times_changed.emit()
        self.saved_times_updated()

    def remove_saved_time(self, row):
        if not 0 <= row < self.saved_time_count:
            return False
        del self.saved_times.rows[row]
        self.saved_times_changed.emit()
        self.saved_times_updated()
        return True

    def edit_saved_time(self, row, name, date_time):
        if not 0 <= row < self.saved_time_count:
            return False
        saved_time = self.saved_time_at(row)
        saved_time.name = name
        saved_time.date = date_time
        self.saved_times_changed.emit()
        self.saved_times_updated()
        return True

    def saved_times_updated(self):
        """Notify the engine after mutating the existing saved-times value."""
        self._world_state_object.saved_times = self._world_state_object.saved_times
        self.world_state_changed.emit()
        self.world_state_object.time_updated()

    def state_loaded(self):
        self.saved_times_changed.emit()
        self.world_state_changed.emit()

    @staticmethod
    def from_object(world_state: WorldStateObject) -> "WorldStateModel":
        model = WorldStateModel(
            world_state_object=world_state,
        )
        world_state.set_ready_callback(model.state_loaded)
        return model

    def to_object(self) -> WorldStateObject:
        return self.world_state_object


class WorldMeshModel(QAbstractTableModel):
    """Read-only summary of the active project's world state."""

    HEADERS = ["Property", "Value"]

    def __init__(self, scene_model=None):
        super().__init__()
        self.scene_model = scene_model
        self.rows: list[tuple[str, str]] = []

    def rowCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        return self.rows[index.row()][index.column()]

    def refresh(self):
        objects = [
            object_base
            for object_base in self._walk_nodes(root_objects.get_nodes())
            if object_base is not world_config
        ]
        scene_objects = list(self.scene_model.objects) if self.scene_model else []
        visible_objects = [
            obj for obj in scene_objects if getattr(obj, "visible", False)
        ]
        rows = [
            ("Mesh objects", str(len(objects))),
            ("Objects in scene", str(len(scene_objects))),
            ("Visible objects", str(len(visible_objects))),
        ]
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    @classmethod
    def _walk_nodes(cls, nodes):
        for node in nodes:
            yield from cls._walk_node(node)

    @classmethod
    def _walk_node(cls, node):
        if node.node_object is not None:
            yield node.node_object
        for child in node.children:
            yield from cls._walk_node(child)
