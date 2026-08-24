from src.components.tree import TreeSearch
from src.dialog.notify import create_notification
from src.objects.object_base import ObjectBase, ViewableMixin

from .registry import ImportBindingRegistry


class ObjectImporterModel:
    """Register domain objects with the active project targets."""

    def __init__(self, table_model, tree_manager, scene_viewer, tree_model=None):
        self.table_model = table_model
        self.tree_manager = tree_manager
        self.scene_viewer = scene_viewer
        self.tree_model = tree_model
        self.block_data_directory = None
        self.project_save_callback = None
        self._project_save_in_progress = False
        from src.components.scene import ShapeController
        from src.components.timer import TimerController

        self.shape_controller = ShapeController(scene_viewer, table_model)
        self.timer_controller = TimerController(scene_viewer)

    def _refresh_tree(self):
        """Reset the tree view's model so stale node indexes are dropped."""
        if self.tree_model is not None and hasattr(self.tree_model, "refresh"):
            self.tree_model.refresh()

    def persist_block(self, block_object):
        """Persist a processed block when the active project has storage."""
        if self.block_data_directory is None:
            return None
        block_path = block_object.serialise_to_directory(self.block_data_directory)
        callback = self.project_save_callback
        if callback is not None and not self._project_save_in_progress:
            self._project_save_in_progress = True
            try:
                callback(block_object)
            finally:
                self._project_save_in_progress = False
        return block_path

    def set_project_save_callback(self, callback):
        """Set the callback used to save project metadata after a block save."""
        self.project_save_callback = callback

    def register(
        self,
        object_base: ObjectBase,
        parent=None,
        add_to_scene=True,
    ):
        """Add an object to the tree and optionally the active scene."""
        block = getattr(object_base, "block_object", None)
        if block is not None and not hasattr(
            object_base, "_importer_destruction_callback"
        ):

            def remove_table_row(_block):
                self.table_model.remove_object(object_base)

            object_base._importer_destruction_callback = remove_table_row
            block.add_destruction_callback(remove_table_row)
        if isinstance(object_base, ViewableMixin):
            object_base.register(
                tree_manager=self.tree_manager,
                parent=parent,
                table_manager=self.table_model if add_to_scene else None,
                scene=self.scene_viewer if add_to_scene else None,
            )
        else:
            object_base.register(self.tree_manager, parent=parent)
        self.sync_block_child_nodes()
        self.shape_controller.attach(object_base)
        self.timer_controller.attach(object_base)
        if not add_to_scene:
            self._refresh_tree()
            return object_base
        self._refresh_tree()
        return object_base

    def sync_block_child_nodes(self):
        """Show registered block relationships as aliases beneath each object."""
        if not hasattr(self.tree_manager, "get_root_nodes"):
            return
        objects = TreeSearch(self.tree_manager.get_root_nodes()).find()
        by_block = {
            getattr(object_base, "block_object", None): object_base
            for object_base in objects
            if getattr(object_base, "block_object", None) is not None
        }
        for object_base in objects:
            node = getattr(object_base, "node", None)
            block = getattr(object_base, "block_object", None)
            if node is None or block is None:
                continue
            children = tuple(
                by_block[child]
                for child in block.relationship_child_block_objects
                if child in by_block and by_block[child] is not object_base
            )
            node.set_block_child_objects(children)

    def remove(self, object_base: ObjectBase):
        """Remove an object from the table, scene, and tree."""
        self.table_model.remove_object(object_base)
        object_base.destroy()
        self._refresh_tree()
        return object_base

    def refresh_object(self, object_base):
        """Refresh persisted, tabular, and visible state after block work."""
        block = getattr(object_base, "block_object", None)
        if block is not None:
            self.persist_block(block)
        if hasattr(self.table_model, "refresh_object"):
            self.table_model.refresh_object(object_base)
        scene = self.scene_viewer
        if scene is not None and hasattr(scene, "refresh_object"):
            scene.refresh_object(object_base)
        return object_base

    def associated_parents(self, object_base):
        """Return tree objects whose blocks reference this object's block."""
        block = getattr(object_base, "block_object", None)
        if block is None:
            return []
        parents = tuple(block._parent_block_objects)
        if not hasattr(self.tree_manager, "get_root_nodes"):
            return []
        search = TreeSearch(self.tree_manager.get_root_nodes())
        return search.find(lambda node: node.block_object in parents)

    def confirm_remove(self, object_base, parent=None):
        """Ask before removing an object referenced by other blocks."""
        associations = self.associated_parents(object_base)
        if not associations:
            return True
        child_block = object_base.block_object
        dependent = set(child_block._parent_dependencies)
        lines = [
            f"{object_base.name} is referenced by the following objects:",
        ]
        for associated in associations:
            relationship = (
                "dependent parent"
                if associated.block_object in dependent
                else "associated parent"
            )
            lines.append(f"- {associated.name} ({relationship})")
        lines.append("Continue deleting this object?")
        dialog = create_notification(
            "Object has dependents",
            "\n".join(lines),
            parent=parent,
            confirm=True,
        )
        return dialog.exec() == dialog.DialogCode.Accepted

    def bind_registered_features(self, tree_view, parent=None, engine_runner=None):
        """Bind all discovered feature importers to this project."""
        return ImportBindingRegistry.bind_all(
            self,
            tree_view,
            parent,
            engine_runner,
        )
