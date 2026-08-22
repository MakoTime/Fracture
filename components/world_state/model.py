from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from components.tree.roots import root_objects, world_config


class WorldStateModel(QAbstractTableModel):
    """Read-only summary of the active project's world state."""

    HEADERS = ["Property", "Value"]

    def __init__(self, scene_model=None):
        super().__init__()
        self.scene_model = scene_model
        self.rows: list[tuple[str, str]] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
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
        visible_objects = [obj for obj in scene_objects if getattr(obj, "visible", False)]
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
