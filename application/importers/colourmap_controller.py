from typing import Optional

from PySide6.QtWidgets import QDialog, QTreeView, QWidget

from components.tree import TreeModel
from components.tree.roots import colourmap_root, root_objects
from dialog.colourmap import ColourmapModel, create_colourmap_dialog
from objects.colourmap import ColourmapObject
from tools.dropdown import create_dropdown_menu
from common.icons import get_icon


class ColourmapController:
    """Create, edit, register, and remove colourmap objects."""

    def __init__(
        self,
        object_importer,
        tree_view: QTreeView,
        parent: Optional[QWidget] = None,
        engine_runner=None,
    ):
        self.object_importer = object_importer
        self.tree_view = tree_view
        self.parent = parent
        self.engine_runner = engine_runner
        if hasattr(tree_view, "add_context_menu_factory"):
            tree_view.add_context_menu_factory(self._create_context_menu_for_index)
        elif hasattr(tree_view, "set_context_menu_factory"):
            tree_view.set_context_menu_factory(self._create_context_menu_for_index)

    def _create_context_menu_for_index(self, index, parent):
        return self.create_context_menu(index.internalPointer(), parent)

    def _deduper(self, exclude=None):
        model = self.tree_view.model() if hasattr(self.tree_view, "model") else None
        if isinstance(model, TreeModel):
            return lambda name: model.next_name(name, exclude=exclude)
        return lambda name: name

    def create_context_menu(self, node, parent=None):
        options = []
        if node is colourmap_root:
            options.append(("New Colourmap", self.create_colourmap))
        elif isinstance(node.node_object, ColourmapObject):
            options.extend(
                (
                    ("Edit", lambda: self.edit(node.node_object)),
                    ("Delete", lambda: self.delete(node.node_object), get_icon("bin")),
                )
            )
        return create_dropdown_menu(options, parent)

    def create_colourmap(self):
        dialog = create_colourmap_dialog(
            parent=self.parent,
            tree_search=self._tree_search(),
            deduper=self._deduper(),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._register(dialog.update_model().to_object())

    def edit(self, colourmap: ColourmapObject):
        dialog = create_colourmap_dialog(
            model=ColourmapModel.from_object(colourmap),
            parent=self.parent,
            tree_search=self._tree_search(),
            deduper=self._deduper(exclude=colourmap),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        updated = dialog.update_model()
        block = colourmap.block_object
        block.comments = updated.comments
        block.update_from(updated)
        colourmap._on_name_changed(updated.name.strip() or colourmap.name)
        block.name = colourmap.name
        self.object_importer.persist_block(block)
        scene = getattr(self.object_importer, "scene_viewer", None)
        if scene is not None and hasattr(scene, "scene_model"):
            for mesh_object in tuple(scene.scene_model.objects):
                if getattr(mesh_object, "colourmap", None) is block:
                    scene.refresh_object_colourmap(mesh_object)
        self._refresh_and_select(colourmap)
        return colourmap

    def delete(self, colourmap: ColourmapObject):
        if not self.object_importer.confirm_remove(colourmap, self.parent):
            return None
        self.object_importer.remove(colourmap)
        self._refresh_and_select(None)
        return colourmap

    def _register(self, colourmap):
        self.object_importer.persist_block(colourmap.block_object)
        self.object_importer.register(
            colourmap,
            parent=colourmap_root,
            add_to_scene=False,
        )
        self._refresh_and_select(colourmap)
        return colourmap

    def _tree_search(self):
        from components.tree import TreeSearch

        return TreeSearch(root_objects.get_nodes())

    def _refresh_and_select(self, colourmap):
        tree_model = self.tree_view.model()
        if not isinstance(tree_model, TreeModel):
            return
        tree_model.refresh()
        if colourmap is None:
            return
        root_index = tree_model.index(
            tree_model.root_data.index(colourmap_root),
            0,
        )
        child_index = tree_model.index(
            colourmap_root.children.index(colourmap.node),
            0,
            root_index,
        )
        self.tree_view.expand(root_index)
        self.tree_view.setCurrentIndex(child_index)
        self.tree_view.scrollTo(child_index)
