from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QIcon

from common.icons import get_icon


class BaseColumn(Enum):
    Name = 0
    Visible = 1
    Object = 2
    Progress = 3
    Shapes = 4
    Other = Shapes
    Remove = 5


@dataclass
class CellObject:
    obj: object
    icon: QIcon


@dataclass
class NormalizedProgressBar:
    value: float


@dataclass
class VisibleField:
    visible: bool
    on_change: callable


@dataclass
class RowData:
    name: str
    visible: VisibleField
    obj: CellObject
    progress: NormalizedProgressBar
    other: object


class TableManager:
    def __init__(self):
        self.columns = list(BaseColumn)
        self.table = []

    def add_row(self, row_data: RowData):
        self.table.append(row_data)

    def get_data(self):
        return self.table


class TableModel(QAbstractTableModel):
    NAME, VISIBLE, OBJECT, PROGRESS, SHAPES, REMOVE = range(6)
    OTHER = SHAPES
    Headers = ["Name", "Visible", "Object", "Progress", "Shapes", "Remove"]

    def __init__(self, table_manager: TableManager):
        super().__init__()
        self.table_manager = table_manager

    def rowCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self.table_manager.get_data())

    def columnCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        return len(self.Headers)

    def add_row(self, row_data: RowData):
        """Insert a row and notify any attached table view."""
        row = self.rowCount()
        self.beginInsertRows(QModelIndex(), row, row)
        self.table_manager.add_row(row_data)
        self.endInsertRows()

    def handle_click(self, index):
        """Handle commands represented by table columns."""
        if index.isValid() and index.column() == self.REMOVE:
            self.remove_row(index.row())

    def remove_row(self, row):
        if row < 0 or row >= self.rowCount():
            return False
        row_data = self.table_manager.get_data()[row]
        object_base = row_data.obj.obj
        self.beginRemoveRows(QModelIndex(), row, row)
        self.table_manager.get_data().pop(row)
        self.endRemoveRows()
        if hasattr(object_base, "remove_from_scene"):
            object_base.remove_from_scene()
        return True

    def remove_object(self, object_base):
        """Remove an object's active scene row, if it is present."""
        for row, row_data in enumerate(self.table_manager.get_data()):
            if row_data.obj.obj is object_base:
                return self.remove_row(row)
        return False

    def refresh_object(self, object_base):
        """Notify views that a registered object's block data changed."""
        for row, row_data in enumerate(self.table_manager.get_data()):
            if row_data.obj.obj is not object_base:
                continue
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1),
            )
            return True
        return False

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row_data = self.table_manager.get_data()[index.row()]
        column = index.column()
        if role == Qt.DisplayRole:
            if column == self.NAME:
                return getattr(row_data.obj.obj, "name", row_data.name)
            if column == self.OBJECT:
                return row_data.obj.obj
            if column == self.PROGRESS:
                return row_data.progress.value
            if column == self.SHAPES:
                return getattr(
                    row_data.obj.obj,
                    "shape_interface",
                    row_data.other,
                )
            if column == self.REMOVE:
                return "Remove"
        elif role == Qt.DecorationRole:
            if column == self.OBJECT:
                return row_data.obj.icon
            if column == self.REMOVE:
                return get_icon("bin")
        return None

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid() and index.column() == self.REMOVE:
            flags |= Qt.ItemFlag.ItemIsEnabled
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or index.column() != self.VISIBLE:
            return False
        if role not in (Qt.CheckStateRole, Qt.EditRole):
            return False

        visible = value in (
            Qt.CheckState.Checked,
            Qt.CheckState.Checked.value,
            True,
        )
        row_data = self.table_manager.get_data()[index.row()]
        row_data.visible.on_change(visible)
        self.dataChanged.emit(index, index, [Qt.CheckStateRole, Qt.DisplayRole])
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.Headers[section]
        return None

    def index(self, row, column, parent=None):
        if parent is None:
            parent = QModelIndex()
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        return self.createIndex(row, column)
