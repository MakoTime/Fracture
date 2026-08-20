from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QIcon


class TreeNode:
    """Represents a node in the tree structure."""

    def __init__(self, name, icon=None, parent=None, node_object=None):
        self.node_object = node_object
        self.name = name
        self.icon = icon if icon else QIcon()
        self.parent = parent
        self.children = []
        self.expanded = False

    def add_child(self, child_node):
        child_node.parent = self
        self.children.append(child_node)

    def remove_child(self, child_node):
        if child_node not in self.children:
            return False
        self.children.remove(child_node)
        child_node.parent = None
        return True


class TreeManager:
    """Manager for handling tree data."""

    def __init__(self):
        self.root_nodes = []

    def add_root_node(self, node):
        if node not in self.root_nodes:
            self.root_nodes.append(node)

    def get_root_nodes(self):
        return self.root_nodes


class TreeModel(QAbstractItemModel):
    """Custom model for managing hierarchical data."""

    def __init__(self, root_data):
        super().__init__()
        self.root_data = root_data

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self.root_data)
        return len(parent.internalPointer().children)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == Qt.DisplayRole:
            return getattr(node.node_object, "name", node.name)
        if role == Qt.DecorationRole:
            return node.icon
        return None

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            child_node = self.root_data[row]
        else:
            child_node = parent.internalPointer().children[row]
        return self.createIndex(row, column, child_node)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_node = index.internalPointer()
        parent_node = child_node.parent
        if parent_node is None:
            return QModelIndex()
        grandparent_node = parent_node.parent
        if grandparent_node is None:
            row = self.root_data.index(parent_node)
        else:
            row = grandparent_node.children.index(parent_node)
        return self.createIndex(row, 0, parent_node)

    def set_expanded(self, index, expanded):
        """Store whether the node represented by an index is expanded."""
        if index.isValid():
            index.internalPointer().expanded = bool(expanded)

    def is_expanded(self, index):
        """Return the stored expansion state for an index."""
        return index.isValid() and index.internalPointer().expanded

    def refresh(self):
        """Notify views that the existing tree nodes may have changed."""
        self.beginResetModel()
        self.endResetModel()