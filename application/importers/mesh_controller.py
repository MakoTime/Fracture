from typing import Optional

from PySide6.QtWidgets import QDialog, QTabWidget, QTreeView, QWidget

from components.tree import TreeModel, TreeSearch
from components.tree.roots import root_objects, transform_root
from components.tree.roots import mesh_root
from dialog.mesh_edit.factory import create_mesh_edit_dialog
from dialog.mesh_colourmap import MeshColourmapModel, create_mesh_colourmap_dialog
from dialog.mesh_generate import GenerateMeshWindow
from dialog.mesh_generate import MeshGenerateModel
from dialog.mesh_filter import MeshFilterModel, create_mesh_filter_dialog
from dialog.mesh_import.factory import (
    create_elevation_import_dialog,
    create_mesh_import_dialog,
)
from dialog.notify import create_notification
from engine import EngineTask
from engine.block_objects import MeshBlockObject
from objects.colourmap import ColourmapObject
from engine.block_tasks import GeneratedMeshTask, MeshFilterTask, MeshImportTask
from engine.block_tasks import PerlinNoiseTransformTask
from objects.mesh_object import MeshObject
from objects.generated_mesh import GeneratedMesh
from objects.perlin_noise_transform import PerlinNoiseTransformObject
from tools.dropdown import create_dropdown_menu
from common.icons import get_icon

from .object_importer import ObjectImporterModel


class MeshImportController:
    """Coordinate mesh import UI, object creation, and registration."""

    BITMAP_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}

    def __init__(
        self,
        object_importer: ObjectImporterModel,
        tree_view: QTreeView,
        parent: Optional[QWidget] = None,
        engine_runner=None,
    ):
        self.object_importer = object_importer
        self.tree_view = tree_view
        self.parent = parent
        self.engine_runner = engine_runner
        self.generate_mesh_window = None
        if hasattr(self.tree_view, "add_context_menu_factory"):
            self.tree_view.add_context_menu_factory(
                self._create_context_menu_for_index
            )
        elif hasattr(self.tree_view, "set_context_menu_factory"):
            self.tree_view.set_context_menu_factory(
                self._create_context_menu_for_index
            )

    def _create_context_menu_for_index(self, index, parent):
        """Adapt the tree view callback to the mesh menu API."""
        return self.create_context_menu(index.internalPointer(), parent)

    def import_mesh(self) -> Optional[EngineTask]:
        """Queue an accepted 3D object mesh import."""
        dialog = create_mesh_import_dialog(parent=self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        model = dialog.update_model()
        if not model.source_path:
            return None
        return self._queue_import(model)

    def import_elevation(self) -> Optional[EngineTask]:
        """Queue an accepted elevation image import."""
        dialog = create_elevation_import_dialog(parent=self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        model = dialog.update_model()
        if not model.source_path:
            return None
        return self._queue_import(model)

    def generate_mesh(self):
        """Open the basic mesh generation workspace in the central tabs."""
        if self.generate_mesh_window is None:
            self.generate_mesh_window = GenerateMeshWindow(
                on_apply=self._register_generated_mesh,
                tree_search=TreeSearch(root_objects.get_nodes()),
            )
            workspace_tabs = (
                self.parent.findChild(QTabWidget, "workspaceTabs")
                if self.parent is not None
                else None
            )
            if workspace_tabs is None:
                self.generate_mesh_window.show()
                return self.generate_mesh_window
            workspace_tabs.addTab(self.generate_mesh_window, "Generate Mesh")
            workspace_tabs.setCurrentWidget(self.generate_mesh_window)
        elif not self.generate_mesh_window.isVisible():
            workspace_tabs = (
                self.parent.findChild(QTabWidget, "workspaceTabs")
                if self.parent is not None
                else None
            )
            if workspace_tabs is not None and workspace_tabs.indexOf(
                self.generate_mesh_window
            ) < 0:
                workspace_tabs.addTab(self.generate_mesh_window, "Generate Mesh")
                workspace_tabs.setCurrentWidget(self.generate_mesh_window)
            else:
                self.generate_mesh_window.show()
        return self.generate_mesh_window

    def edit_generation(self, mesh_object: GeneratedMesh):
        """Open generation settings and replace the existing generated mesh."""
        window = GenerateMeshWindow(
            model=MeshGenerateModel.from_generated_mesh(mesh_object),
            on_apply=lambda edited: self._replace_generated_mesh(mesh_object, edited),
            tree_search=TreeSearch(root_objects.get_nodes()),
        )
        workspace_tabs = (
            self.parent.findChild(QTabWidget, "workspaceTabs")
            if self.parent is not None
            else None
        )
        if workspace_tabs is None:
            window.show()
        else:
            workspace_tabs.addTab(window, "Edit Generation")
            workspace_tabs.setCurrentWidget(window)
        return window

    def filter_mesh(self, mesh_object: GeneratedMesh):
        """Open the mesh filter workspace for an existing generated mesh."""
        transforms = tuple(
            node.node_object
            for node in transform_root.children
            if isinstance(node.node_object, PerlinNoiseTransformObject)
        )
        window = create_mesh_filter_dialog(
            MeshFilterModel.from_mesh(mesh_object),
            parent=self.parent,
            on_apply=lambda model: self._register_filtered_mesh(
                model.generate(), mesh_object, model
            ),
            transforms=tuple(transforms),
        )
        workspace_tabs = (
            self.parent.findChild(QTabWidget, "workspaceTabs")
            if self.parent is not None
            else None
        )
        if workspace_tabs is None:
            window.show()
            return window
        workspace_tabs.addTab(window, "Filter Mesh")
        workspace_tabs.setCurrentWidget(window)
        return window

    def _register_filtered_mesh(self, filtered_mesh, source_mesh, filter_model=None):
        self.object_importer.persist_block(filtered_mesh.mesh_block_object)
        self.object_importer.register(
            filtered_mesh,
            parent=mesh_root,
            add_to_scene=True,
        )
        self._sync_generated_mesh_children(filtered_mesh)
        self._bind_generated_mesh_tasks(source_mesh)
        self._bind_filtered_mesh_task(
            filtered_mesh,
            source_mesh,
            filter_model,
        )
        self._show_mesh(filtered_mesh)
        return filtered_mesh

    def _bind_filtered_mesh_task(
        self,
        filtered_mesh,
        source_mesh,
        filter_model,
    ):
        if filter_model is None or self.engine_runner is None:
            return None
        transform_block = filter_model._transform_block()
        if hasattr(self.engine_runner, "enqueue_block_task"):
            self.engine_runner.enqueue_block_task(
                f"Configure {transform_block.name}",
                PerlinNoiseTransformTask(transform_block),
            )
        task = MeshFilterTask(
            source_mesh.mesh_block_object,
            transform_block,
            filter_model.noise_minimum,
            filter_model.noise_maximum,
            filter_model.noise_penetration,
            block_object=filtered_mesh.mesh_block_object,
        )
        if not hasattr(self.engine_runner, "enqueue_block_task"):
            return None
        if hasattr(self.engine_runner, "task_model"):
            return self.engine_runner.enqueue_block_task(
                f"Filter {filtered_mesh.name}",
                task,
                on_finished=lambda finished: self._finish_task(filtered_mesh, finished),
            )
        return self.engine_runner.enqueue_block_task(f"Filter {filtered_mesh.name}", task)

    def _replace_generated_mesh(self, mesh_object, edited_mesh):
        was_visible = mesh_object.visible
        colourmap = mesh_object.colourmap
        mesh_object.remove_from_scene()
        mesh_object.mesh_block_object = edited_mesh.mesh_block_object
        mesh_object.mesh_block_object.set_colourmap(colourmap)
        mesh_object.name = edited_mesh.name
        mesh_object.metadata.update(edited_mesh.metadata)
        self.object_importer.persist_block(mesh_object.mesh_block_object)
        self._sync_generated_mesh_children(mesh_object)
        self._bind_generated_mesh_tasks(mesh_object)
        if was_visible:
            self.show_mesh(mesh_object)
        self.tree_view.model().refresh()
        return mesh_object

    def _register_generated_mesh(self, mesh_object):
        """Persist and register a generated mesh when a project is available."""
        if self.object_importer is None or not hasattr(
            self.object_importer, "register"
        ):
            return mesh_object
        self.object_importer.persist_block(mesh_object.mesh_block_object)
        self.object_importer.register(
            mesh_object,
            parent=mesh_root,
            add_to_scene=False,
        )
        self._sync_generated_mesh_children(mesh_object)
        self._bind_generated_mesh_tasks(mesh_object)
        self._show_mesh(mesh_object)
        return mesh_object

    def _sync_generated_mesh_children(self, mesh_object):
        return self._sync_mesh_children(mesh_object)

    def _sync_mesh_children(self, mesh_object):
        block_children = mesh_object.mesh_block_object.child_block_objects
        transforms = TreeSearch(root_objects.get_nodes()).find(
            lambda node: node.block_object in block_children
        )
        mesh_object.node.set_block_child_objects(transforms)

    def _bind_generated_mesh_tasks(self, mesh_object):
        if self.engine_runner is None or not hasattr(
            self.engine_runner, "enqueue_block_task"
        ):
            return
        block = mesh_object.mesh_block_object
        child = block.perlin_noise_transform
        if child is not None:
            self.engine_runner.enqueue_block_task(
                f"Configure {child.name}",
                PerlinNoiseTransformTask(child),
            )
        model = MeshGenerateModel.from_generated_mesh(mesh_object)
        parent_task = GeneratedMeshTask(model, block)
        if hasattr(self.engine_runner, "task_model"):
            self.engine_runner.enqueue_block_task(
                f"Regenerate {mesh_object.name}",
                parent_task,
                on_finished=lambda finished: self._finish_task(mesh_object, finished),
            )
        else:
            self.engine_runner.enqueue_block_task(
                f"Regenerate {mesh_object.name}",
                parent_task,
            )

    def _finish_task(self, mesh_object, task):
        if task.error:
            return
        self.object_importer.refresh_object(mesh_object)

    def edit_mesh(self, mesh_object: MeshObject):
        """Edit an existing mesh after the dialog is accepted."""
        colourmaps = TreeSearch(root_objects.get_nodes()).find(
            lambda node: isinstance(node.node_object, ColourmapObject)
        )
        dialog = create_mesh_edit_dialog(
            mesh_object,
            colourmaps=tuple(colourmaps),
            parent=self.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        edited_model = dialog.update_model()
        edited_mesh = edited_model.apply()
        self._sync_mesh_children(edited_mesh)
        self.object_importer.persist_block(edited_mesh.mesh_block_object)
        scene = getattr(self.object_importer, "scene_viewer", None)
        if scene is not None and hasattr(scene, "refresh_object_colourmap"):
            scene.refresh_object_colourmap(edited_mesh)
        self.tree_view.model().refresh()
        return edited_mesh

    def edit_mesh_colourmap(self, mesh_object: MeshObject):
        """Open the colourmap editor as a workspace tab."""
        colourmaps = TreeSearch(root_objects.get_nodes()).find(
            lambda node: isinstance(node.node_object, ColourmapObject)
        )
        field1, field2 = mesh_object.colourmap_field_sources
        invert1, invert2 = mesh_object.colourmap_field_inversions
        selected = next(
            (
                colourmap
                for colourmap in colourmaps
                if getattr(colourmap, "block_object", colourmap)
                is mesh_object.colourmap
            ),
            None,
        )
        def apply_colourmap(model):
            model.apply(mesh_object)
            self._sync_mesh_children(mesh_object)
            self.object_importer.persist_block(mesh_object.mesh_block_object)
            scene = getattr(self.object_importer, "scene_viewer", None)
            if scene is not None and hasattr(scene, "refresh_object_colourmap"):
                scene.refresh_object_colourmap(mesh_object)
            tree_model = self.tree_view.model()
            if isinstance(tree_model, TreeModel):
                tree_model.refresh()

        window = create_mesh_colourmap_dialog(
            MeshColourmapModel(
                mesh_object=mesh_object,
                colourmap=selected,
                field1_source=field1,
                field2_source=field2,
                invert_field1=invert1,
                invert_field2=invert2,
            ),
            colourmaps=tuple(colourmaps),
            parent=self.parent,
            on_apply=apply_colourmap,
        )
        workspace_tabs = (
            self.parent.findChild(QTabWidget, "workspaceTabs")
            if self.parent is not None
            else None
        )
        if workspace_tabs is None:
            window.show()
            return window
        workspace_tabs.addTab(window, "Edit Mesh Colourmap")
        workspace_tabs.setCurrentWidget(window)
        return window

    def _queue_import(self, model) -> Optional[EngineTask]:
        """Queue a mesh model and register it after engine processing."""

        import_task = model.to_mesh_import_task()

        def finish_import(task):
            if task is not None and task.error:
                return
            self.object_importer.persist_block(import_task.block_object)
            if not model.add_to_scene:
                import_task.block_object.release()
            mesh_object = model.to_mesh_object(
                import_task.block_object
            )
            if model.add_to_scene:
                mesh_object.set_visible(True)
            self.object_importer.register(
                mesh_object,
                parent=mesh_root,
                add_to_scene=model.add_to_scene,
            )
            self._show_mesh(mesh_object)

        if self.engine_runner is None:
            import_task.execute(import_task.prepare())
            finish_import(None)
            return None

        if hasattr(self.engine_runner, "enqueue_block_task"):
            return self.engine_runner.enqueue_block_task(
                f"Import {model.file_name}",
                import_task,
                on_finished=finish_import,
            )
        return self.engine_runner.enqueue_task(
            f"Import {model.file_name}",
            lambda progress: import_task.execute(import_task.prepare(), progress),
            on_finished=finish_import,
        )

    def create_context_menu(self, node, parent: Optional[QWidget] = None):
        """Create actions appropriate for a tree node."""
        options = []
        if node is mesh_root:
            options.append(("Generate Mesh", self.generate_mesh))
            options.append(("Import mesh from 3D object", self.import_mesh))
            options.append(("Import Mesh from elevation data", self.import_elevation))
        elif isinstance(node.node_object, MeshObject):
            if isinstance(node.node_object, GeneratedMesh):
                options.append(
                    (
                        "Edit Generation",
                        lambda: self.edit_generation(node.node_object),
                    )
                )
                options.append(
                    (
                        "Filter Mesh",
                        lambda: self.filter_mesh(node.node_object),
                    )
                )
            options.append(
                (
                    "Edit Colourmap",
                    lambda: self.edit_mesh_colourmap(node.node_object),
                )
            )
            options.append(("Edit Mesh", lambda: self.edit_mesh(node.node_object)))
            options.append(("Show in scene", lambda: self.show_mesh(node.node_object)))
            options.append(
                ("Delete", lambda: self.delete_mesh(node.node_object), get_icon("bin"))
            )
        return create_dropdown_menu(options, parent)

    def show_mesh(self, mesh_object: MeshObject):
        """Add a mesh to the active scene pipeline if it is not already loaded."""
        mesh_data = mesh_object.mesh_data
        if mesh_data is None or (
            hasattr(mesh_data, "n_points") and mesh_data.n_points == 0
        ):
            dialog = create_notification(
                "Cannot show mesh",
                "This mesh has no surface points to display.",
                parent=self.parent,
            )
            dialog.exec()
            return None
        mesh_object.set_visible(True)
        self.object_importer.register(mesh_object, parent=mesh_root)
        return mesh_object

    def delete_mesh(self, mesh_object: MeshObject):
        """Delete a mesh from the application while preserving no references."""
        if not self.object_importer.confirm_remove(mesh_object, self.parent):
            return None
        self.object_importer.remove(mesh_object)
        tree_model = self.tree_view.model()
        if isinstance(tree_model, TreeModel):
            tree_model.refresh()
        return mesh_object

    @staticmethod
    def _load_mesh(model):
        """Load a mesh synchronously for compatibility with existing callers."""
        task = model.to_mesh_import_task()
        task.execute(task.prepare())
        return task.block_object.mesh_data

    def _show_mesh(self, mesh_object: MeshObject):
        """Refresh the tree and reveal the newly registered mesh."""
        tree_model = self.tree_view.model()
        if not isinstance(tree_model, TreeModel):
            return

        tree_model.refresh()
        mesh_root_index = tree_model.index(
            tree_model.root_data.index(mesh_root),
            0,
        )
        self.tree_view.expand(mesh_root_index)
        mesh_index = tree_model.index(
            mesh_root.children.index(mesh_object.node),
            0,
            mesh_root_index,
        )
        self.tree_view.setCurrentIndex(mesh_index)
        self.tree_view.scrollTo(mesh_index)
