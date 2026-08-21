
from contextlib import contextmanager
from typing import Any, Optional
from uuid import uuid4

from PySide6.QtGui import QIcon

from components.table import CellObject, NormalizedProgressBar, RowData, VisibleField
from components.tree import TreeNode, root_objects


class ObjectBase:
    def __init__(
        self,
        name: str,
        icon: Optional[QIcon] = None,
        visible: bool = True,
        progress: float = 0.0,
        other: Any = None,
        metadata: Optional[dict[str, Any]] = None,
        scene_data: Any = None,
        guid: Optional[str] = None,
        auto_register_root: bool = True,
    ):
        self.name = name
        self.guid = guid or str(uuid4())
        self.icon = icon if icon is not None else QIcon()
        self.visible = visible
        self.progress = self._normalize_progress(progress)
        self.metadata = metadata if metadata is not None else {}
        self.scene_data = scene_data
        self._scene = None
        self._table_manager = None
        self._change_depth = 0
        self._destroyed = False

        self.node = TreeNode(
            name=self.name,
            icon=self.icon,
            node_object=self,
        )
        block = getattr(self, "block_object", None)
        if block is not None and hasattr(block, "add_destruction_callback"):
            block.add_destruction_callback(self._on_block_destroyed)
        if block is not None and hasattr(block, "add_change_callback"):
            block.add_change_callback(self._on_block_changed)
        if auto_register_root:
            root_objects.add(self.node)
        self.row_data = RowData(
            name=self.name,
            visible=VisibleField(self.visible, self._on_visible_changed),
            obj=CellObject(self, self.icon),
            progress=NormalizedProgressBar(self.progress),
            other=other,
        )

    def add_to_table(self, table_manager):
        """Add this object's table representation to a table manager."""
        self._table_manager = table_manager
        block = getattr(self, "block_object", None)
        if block is not None and hasattr(block, "add_destruction_callback"):
            block.add_destruction_callback(self._on_block_destroyed)
        if block is not None and hasattr(block, "add_change_callback"):
            block.add_change_callback(self._on_block_changed)
        rows = (
            table_manager.get_data()
            if hasattr(table_manager, "get_data")
            else table_manager.table_manager.get_data()
        )
        if self.row_data not in rows:
            table_manager.add_row(self.row_data)
        return self.row_data

    def add_to_tree(self, tree_manager, parent=None):
        """Add this object's tree node as a root or child node."""
        if parent is None:
            tree_manager.add_root_node(self.node)
        elif self.node.parent is not parent:
            parent.add_child(self.node)
        return self.node

    def add_to_scene(self, scene):
        """Add this object to a scene container."""
        if self._scene is scene:
            return self
        self._scene = scene
        if hasattr(scene, "add_object"):
            scene.add_object(self)
        elif hasattr(scene, "add"):
            scene.add(self)
        elif hasattr(scene, "append"):
            scene.append(self)
        else:
            raise TypeError(
                "scene must provide add_object(), add(), or append()"
            )
        return self

    def remove_from_scene(self):
        """Remove this object from its registered scene, if any."""
        if self._scene is None or not hasattr(self._scene, "remove_object"):
            return False
        removed = self._scene.remove_object(self)
        if removed:
            self._scene = None
        return removed

    def remove_from_tree(self):
        """Remove this object's node from its current tree parent or roots."""
        return root_objects.remove_object(self)

    def destroy(self):
        """Destroy this object and its engine block, then remove its views."""
        if self._destroyed:
            return self
        self._destroyed = True
        block = getattr(self, "block_object", None)
        if block is not None and not block.is_destroyed():
            block.destroy()
        self._detach_representations()
        return self

    def _on_block_destroyed(self, block):
        del block
        self._destroyed = True
        self._detach_representations()

    def _on_block_changed(self, block):
        if self._table_manager is not None and hasattr(
            self._table_manager, "refresh_object"
        ):
            self._table_manager.refresh_object(self)
        if self._scene is not None and hasattr(self._scene, "refresh_object"):
            self._scene.refresh_object(self)

    def _detach_representations(self):
        """Remove scene, table, and tree representations owned by this object."""
        if self._table_manager is not None and hasattr(
            self._table_manager, "remove_object"
        ):
            self._table_manager.remove_object(self)
        self._table_manager = None
        self.remove_from_scene()
        self.remove_from_tree()
        self.node.children.clear()

    def set_visible(self, visible: bool):
        """Update visibility through the same callback used by the table."""
        self.row_data.visible.on_change(bool(visible))
        return self.visible

    def register(self, table_manager=None, tree_manager=None, scene=None, parent=None):
        """Register this object with any supplied table, tree, and scene targets."""
        if table_manager is not None:
            self.add_to_table(table_manager)
        if tree_manager is not None:
            self.add_to_tree(tree_manager, parent)
        if scene is not None:
            self.add_to_scene(scene)
        return self

    @staticmethod
    def _normalize_progress(progress: float) -> float:
        return max(0.0, min(1.0, float(progress)))

    @contextmanager
    def _changing(self):
        """Allow only the outermost change to update object state."""
        if self._change_depth:
            yield False
            return

        self._change_depth += 1
        try:
            yield True
        finally:
            self._change_depth -= 1

    def _on_visible_changed(self, visible):
        """Handle changes in visibility."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.visible = bool(visible)
            if self.row_data is not None:
                self.row_data.visible.visible = self.visible
            if self._scene is not None and hasattr(
                self._scene,
                "set_object_visibility",
            ):
                self._scene.set_object_visibility(self, self.visible)

    def _on_progress_changed(self, progress):
        """Handle changes in progress."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.progress = self._normalize_progress(progress)
            if self.row_data is not None:
                self.row_data.progress.value = self.progress

    def _on_name_changed(self, name):
        """Handle changes in name."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.name = name
            if self.node is not None:
                self.node.name = name
            if self.row_data is not None:
                self.row_data.name = name

    def _on_icon_changed(self, icon):
        """Handle changes in icon."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.icon = icon if icon is not None else QIcon()
            if self.node is not None:
                self.node.icon = self.icon
            if self.row_data is not None:
                self.row_data.obj.icon = self.icon
    