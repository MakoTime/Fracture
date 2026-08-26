from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from PySide6.QtGui import QIcon

from src.components.table import (
    CellObject,
    NormalizedProgressBar,
    RowData,
    VisibleField,
)
from src.components.tree.model import TreeNode
from src.components.tree.roots.root_objects import root_objects


class BaseMixin:
    def _detach_other_representations(self):
        pass


class ViewableMixin(BaseMixin):
    """Adds scene/table representation to an ObjectBase."""

    def __init__(
        self,
        visible: bool = True,
        scene_data: Any = None,
        other: Any = None,
        **kwargs,
    ):
        self.visible = visible
        self.scene_data = scene_data
        self._scene = None
        self._table_manager = None
        super().__init__(**kwargs)
        self.row_data = RowData(
            name=self.name,
            visible=VisibleField(self.visible, self._on_visible_changed),
            obj=CellObject(self, self.icon),
            progress=NormalizedProgressBar(self.progress),
            other=other,
        )

    def register(
        self,
        tree_manager,
        parent=None,
        table_manager=None,
        scene=None,
    ):
        super().register(tree_manager, parent)
        if table_manager is not None:
            self.add_to_table(table_manager)
        if scene is not None:
            self.add_to_scene(scene)
        return self

    def add_to_table(self, table_manager):
        self._table_manager = table_manager

        rows = (
            table_manager.get_data()
            if hasattr(table_manager, "get_data")
            else table_manager.table_manager.get_data()
        )

        if self.row_data not in rows:
            table_manager.add_row(self.row_data)

        return self.row_data

    def add_to_scene(self, scene):
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
            raise TypeError("scene must provide add_object(), add(), or append()")

        return self

    def remove_from_scene(self):
        if self._scene is None:
            return False

        if not hasattr(self._scene, "remove_object"):
            return False

        removed = self._scene.remove_object(self)

        if removed:
            self._scene = None

        return removed

    def on_selected(self):
        """Handle selection of the object in the scene or table."""

    def set_visible(self, visible: bool):
        self.row_data.visible.on_change(bool(visible))
        return self.visible

    def _on_visible_changed(self, visible):
        with self._changing() as is_outermost:
            if not is_outermost:
                return

            self.visible = bool(visible)
            self.row_data.visible.visible = self.visible

            if self._scene is not None and hasattr(
                self._scene, "set_object_visibility"
            ):
                self._scene.set_object_visibility(
                    self,
                    self.visible,
                )

    def _detach_other_representations(self):
        if self._table_manager is not None and hasattr(
            self._table_manager, "remove_object"
        ):
            self._table_manager.remove_object(self)

        self._table_manager = None
        self.remove_from_scene()
        super()._detach_other_representations()


class ObjectBase:
    def __init__(
        self,
        name: str,
        icon: QIcon | None = None,
        progress: float = 0.0,
        metadata: dict[str, Any] | None = None,
        guid: str | None = None,
        auto_register_root: bool = True,
        register_in_tree: bool = True,
    ):
        self.name = name
        self.guid = guid or str(uuid4())
        self.icon = icon if icon is not None else QIcon()
        self.progress = self._normalize_progress(progress)
        self.metadata = metadata if metadata is not None else {}
        self._change_depth = 0
        self._destroyed = False

        self.node = TreeNode(
            name=self.name,
            icon=self.icon,
            node_object=self,
        )

        block = getattr(self, "block_object", None)
        if block is not None:
            if hasattr(block, "add_destruction_callback"):
                block.add_destruction_callback(self._on_block_destroyed)
            if hasattr(block, "add_change_callback"):
                block.add_change_callback(self._on_block_changed)

        if auto_register_root:
            root_objects.add(self.node)

    # tree stuff
    def register(self, tree_manager, parent=None):
        return self.add_to_tree(tree_manager, parent)

    def add_to_tree(self, tree_manager, parent=None):
        if parent is None:
            tree_manager.add_root_node(self.node)
        elif self.node.parent is not parent:
            parent.add_child(self.node)
        return self.node

    def remove_from_tree(self):
        return root_objects.remove_object(self)

    # lifecycle
    def destroy(self):
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
        if hasattr(self, "_table_manager"):
            table_manager = self._table_manager
            if table_manager is not None and hasattr(table_manager, "refresh_object"):
                table_manager.refresh_object(self)

        if hasattr(self, "_scene"):
            scene = self._scene
            if scene is not None and hasattr(scene, "refresh_object"):
                scene.refresh_object(self)

    def _detach_representations(self):
        self._detach_tree_representations()  # Renamed to avoid recursion
        self._detach_other_representations()

    def _detach_tree_representations(self):
        self.remove_from_tree()

        for child in tuple(self.node.children):
            self.node.remove_child(child)

    def _detach_other_representations(self):
        pass  # Placeholder for any additional detachment logic

    @staticmethod
    def _normalize_progress(progress: float) -> float:
        return max(0.0, min(1.0, float(progress)))

    # common change handling
    @contextmanager
    def _changing(self):
        if self._change_depth:
            yield False
            return

        self._change_depth += 1
        try:
            yield True
        finally:
            self._change_depth -= 1

    def _on_progress_changed(self, progress):
        """Handle changes in progress."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.progress = self._normalize_progress(progress)
            if hasattr(self, "row_data"):
                self.row_data.progress.value = self.progress

    def _on_name_changed(self, name):
        """Handle changes in name."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.name = name
            if self.node is not None:
                self.node.name = name
            if hasattr(self, "row_data"):
                self.row_data.name = name

    def _on_icon_changed(self, icon):
        """Handle changes in icon."""
        with self._changing() as is_outermost:
            if not is_outermost:
                return
            self.icon = icon if icon is not None else QIcon()
            if self.node is not None:
                self.node.icon = self.icon
            if hasattr(self, "row_data"):
                self.row_data.obj.icon = self.icon
