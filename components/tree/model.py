import re

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QIcon


def has_name_attribute(object_base):
    """Return whether an object has a given name."""
    try:
        return isinstance(object_base.name, str)
    except AttributeError as e:
        raise ValueError(
            f"Object {object_base} does not have a name attribute: {e}"
        ) from e


class TreeNode:
    """Represents a node in the tree structure."""

    def __init__(self, name, icon=None, parent=None, node_object=None):
        self.node_object = node_object
        self.name = name
        self.icon = icon if icon else QIcon()
        self.parent = parent
        self.children = []
        self._block_child_nodes = []
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

    def remove_object_nodes(self, node_object):
        """Remove every descendant node representing ``node_object``."""
        removed = False
        for child in tuple(self.children):
            if child.node_object is node_object:
                self.remove_child(child)
                removed = True
                continue
            removed = child.remove_object_nodes(node_object) or removed
        return removed

    def set_block_child_objects(self, objects):
        """Show existing project objects for this node's block children."""
        for child_node in tuple(self._block_child_nodes):
            self.remove_child(child_node)
        self._block_child_nodes.clear()
        for object_base in objects:
            child_node = TreeNode(
                name=object_base.name,
                icon=object_base.icon,
                node_object=object_base,
            )
            child_node.is_block_child = True
            self.add_child(child_node)
            self._block_child_nodes.append(child_node)
        return tuple(self._block_child_nodes)

    @property
    def block_object(self):
        """Return the engine block owned by this node's project object."""
        return getattr(self.node_object, "block_object", None)

    def get_block_objects(self):
        """Return this node's block and the blocks owned by its descendants."""
        blocks = []
        if self.block_object is not None:
            blocks.append(self.block_object)
        for child in self.children:
            blocks.extend(child.get_block_objects())
        return blocks


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

    def __init__(self, root_data, duplicate_name_handler=None):
        super().__init__()
        self.root_data = root_data
        self.duplicate_name_handler = duplicate_name_handler

    def rowCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        if not parent.isValid():
            return len(self.root_data)
        return len(parent.internalPointer().children)

    def columnCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
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

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid() and index.internalPointer().node_object is not None:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        node = index.internalPointer()
        object_base = node.node_object
        if object_base is None:
            return False
        name = str(value).strip()
        if not name:
            return False
        if self.is_name_used(name, exclude=object_base):
            if self.duplicate_name_handler is None:
                return False
            name = self.duplicate_name_handler(name, object_base)
            if name is None:
                return False
        object_base._on_name_changed(name)
        block_object = getattr(object_base, "block_object", None)
        if block_object is not None:
            block_object.name = name
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
        return True

    def names(self, exclude=None):
        names = set()
        seen = set()

        def collect(node):
            object_base = node.node_object
            if object_base is not None:
                identity = id(object_base)
                if identity not in seen:
                    seen.add(identity)
                    if object_base is not exclude:
                        names.add(str(getattr(object_base, "name", "")))
            for child in node.children:
                collect(child)

        for root in self.root_data:
            collect(root)
        return names

    def is_name_used(self, name, exclude=None):
        return str(name).strip() in self.names(exclude=exclude)

    def next_name(self, prefix, exclude=None):
        prefix = str(prefix).strip() or "Object"
        match = re.match(r"^(.*) \d{3}$", prefix)
        if match:
            prefix = match.group(1)
        names = self.names(exclude=exclude)
        if prefix not in names:
            return prefix
        number = 1
        while f"{prefix} {number:03d}" in names:
            number += 1
        return f"{prefix} {number:03d}"
    
    @staticmethod
    def next_name_static(prefix, exclude=None):
        prefix = str(prefix).strip() or "Object"
        match = re.match(r"^(.*) \d{3}$", prefix)
        if match:
            prefix = match.group(1)
        names = {
            obj.name
            for obj in existing_objects
            if obj is not exclude and has_name_attribute(obj)
        }
        if prefix not in names:
            return prefix
        number = 1
        while f"{prefix} {number:03d}" in names:
            number += 1
        return f"{prefix} {number:03d}"

    def index(self, row, column, parent=None):
        if parent is None:
            parent = QModelIndex()
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
