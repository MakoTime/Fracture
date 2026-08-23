from PySide6.QtWidgets import QDialog, QTreeView, QWidget

from components.tree import TreeModel
from components.tree.roots import world_config
from dialog.world_config import create_world_config_dialog
from tools.dropdown import create_dropdown_menu


class WorldConfigController:
    """Provide editing for the always-present world configuration object."""

    def __init__(self, tree_view: QTreeView, parent: QWidget | None = None):
        self.tree_view = tree_view
        self.parent = parent
        if hasattr(tree_view, "add_context_menu_factory"):
            tree_view.add_context_menu_factory(self._create_context_menu_for_index)
        elif hasattr(tree_view, "set_context_menu_factory"):
            tree_view.set_context_menu_factory(self._create_context_menu_for_index)

    def _create_context_menu_for_index(self, index, parent):
        return self.create_context_menu(index.internalPointer(), parent)

    def create_context_menu(self, node, parent=None):
        if node is not world_config.node:
            return create_dropdown_menu((), parent)
        return create_dropdown_menu(
            (("Edit", self.edit),),
            parent,
        )

    def edit(self):
        model = self.tree_view.model() if hasattr(self.tree_view, "model") else None
        if isinstance(model, TreeModel):
            deduper = lambda name: model.next_name(name, exclude=world_config)
        else:
            deduper = lambda name: name
        dialog = create_world_config_dialog(
            world_config, parent=self.parent, deduper=deduper
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.apply_changes()