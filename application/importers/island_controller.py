from PySide6.QtWidgets import QTabWidget, QTreeView, QWidget

from common.icons import get_icon
from components.tree import TreeModel, TreeSearch
from components.tree.roots import island_root, world_config
from objects.mesh_object import MeshObject
from dialog.island import create_island_dialog
from engine.block_objects import IslandBlockObject
from engine.block_tasks import IslandTask
from objects.island import Island
from tools.dropdown import create_dropdown_menu


class IslandController:
    """Provide editing for Island objects."""

    def __init__(self, object_importer, tree_view: QTreeView, parent: QWidget | None = None, engine_runner=None):
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

    def _deduper(self):
        model = self.tree_view.model() if hasattr(self.tree_view, "model") else None
        if isinstance(model, TreeModel):
            return model.next_name
        return lambda name: name

    def create_context_menu(self, node, parent=None):
        if node is island_root:
            return create_dropdown_menu(
                (("Add Island", self.add_island),),
                parent,
            )
        if isinstance(node.node_object, Island):
            return create_dropdown_menu(
                (("Edit", lambda: self.edit(node.node_object)),
                 ("Delete", lambda: self.delete(node.node_object), get_icon("bin"))),
                parent,
            )
        return create_dropdown_menu((), parent)

    def _source_meshes(self):
        meshes = TreeSearch(self.tree_view.model().root_data).find(
            lambda node: isinstance(node.node_object, MeshObject)
        )
        return tuple(meshes)

    def add_island(self):
        source_meshes = self._source_meshes()
        block = IslandBlockObject(world_config=world_config.block_object)
        island = Island(block_object=block, auto_register_root=False)
        island.show_in_scene = True
        dialog = create_island_dialog(
            island,
            parent=self.parent,
            source_meshes=source_meshes,
            deduper=self._deduper(),
            new_island=True,
            on_apply=lambda result: self._register_new_island(result),
        )
        tabs = self.parent.findChild(QTabWidget, "workspaceTabs") if self.parent else None
        if tabs is None:
            dialog.show()
        else:
            tabs.addTab(dialog, "Add Island")
            tabs.setCurrentWidget(dialog)
        return dialog

    def _register_new_island(self, island):
        self.object_importer.register(island, parent=island_root, add_to_scene=False)
        model = self.tree_view.model()
        if hasattr(model, "refresh"):
            model.refresh()
        return self._apply(island)

    def edit(self, island):
        source_meshes = self._source_meshes()
        dialog = create_island_dialog(
            island,
            parent=self.parent,
            on_apply=self._apply,
            source_meshes=source_meshes,
        )
        tabs = (
            self.parent.findChild(QTabWidget, "workspaceTabs")
            if self.parent is not None
            else None
        )
        if tabs is None:
            dialog.show()
        else:
            tabs.addTab(dialog, "Edit Island")
            tabs.setCurrentWidget(dialog)
        return dialog

    def _apply(self, island):
        self._enqueue_task(island)
        if self.engine_runner is None or not hasattr(
            self.engine_runner, "enqueue_block_task"
        ):
            self.object_importer.refresh_object(island)
        return island

    def _enqueue_task(self, island):
        if self.engine_runner is None or not hasattr(
            self.engine_runner, "enqueue_block_task"
        ):
            return None
        task = IslandTask(island.block_object)
        return self.engine_runner.enqueue_block_task(
            f"Update {island.name}",
            task,
            on_finished=lambda finished: self._finish(island, finished),
        )

    def bind_loaded_tasks(self, loaded_objects):
        """Bind regeneration tasks for Islands restored from a project."""
        for island in loaded_objects:
            if isinstance(island, Island):
                self._enqueue_task(island)

    def _finish(self, island, task):
        if not getattr(task, "error", None):
            if getattr(island, "show_in_scene", False):
                self.object_importer.register(
                    island,
                    parent=island_root,
                    add_to_scene=True,
                )
            else:
                island.remove_from_scene()
            self.object_importer.refresh_object(island)
            model = self.tree_view.model()
            if hasattr(model, "refresh"):
                model.refresh()

    def delete(self, island):
        if self.object_importer.confirm_remove(island, parent=self.parent):
            removed = self.object_importer.remove(island)
            model = self.tree_view.model()
            if hasattr(model, "refresh"):
                model.refresh()
            return removed
        return None