from objects.object_base import ObjectBase

from .registry import ImportBindingRegistry


class ObjectImporterModel:
    """Register domain objects with the active project targets."""

    def __init__(self, table_model, tree_manager, scene_viewer):
        self.table_model = table_model
        self.tree_manager = tree_manager
        self.scene_viewer = scene_viewer

    def register(
        self,
        object_base: ObjectBase,
        parent=None,
        add_to_scene=True,
    ):
        """Add an object to the tree and optionally the active scene."""
        object_base.add_to_tree(self.tree_manager, parent=parent)
        if not add_to_scene:
            return object_base
        object_base.register(
            table_manager=self.table_model,
            tree_manager=self.tree_manager,
            scene=self.scene_viewer,
            parent=parent,
        )
        return object_base

    def remove(self, object_base: ObjectBase):
        """Remove an object from the table, scene, and tree."""
        if not self.table_model.remove_object(object_base):
            object_base.remove_from_scene()
        object_base.remove_from_tree()
        return object_base

    def bind_registered_features(self, tree_view, parent=None):
        """Bind all discovered feature importers to this project."""
        return ImportBindingRegistry.bind_all(self, tree_view, parent)
