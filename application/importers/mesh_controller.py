from typing import Optional

import pyvista as pv
from PySide6.QtWidgets import QDialog, QTreeView, QWidget

from components.tree import TreeModel
from components.tree.roots import mesh_root
from dialog.mesh.factory import create_mesh_import_dialog
from objects.mesh_object import MeshObject
from tools.dropdown import create_dropdown_menu

from .object_importer import ObjectImporterModel


class MeshImportController:
    """Coordinate mesh import UI, object creation, and registration."""

    def __init__(
        self,
        object_importer: ObjectImporterModel,
        tree_view: QTreeView,
        parent: Optional[QWidget] = None,
    ):
        self.object_importer = object_importer
        self.tree_view = tree_view
        self.parent = parent
        if hasattr(self.tree_view, "set_context_menu_factory"):
            self.tree_view.set_context_menu_factory(
                self._create_context_menu_for_index
            )

    def _create_context_menu_for_index(self, index, parent):
        """Adapt the tree view callback to the mesh menu API."""
        return self.create_context_menu(index.internalPointer(), parent)

    def import_mesh(self) -> Optional[MeshObject]:
        """Show the import dialog and register an accepted mesh."""
        dialog = create_mesh_import_dialog(parent=self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        model = dialog.update_model()
        if not model.source_path:
            return None

        model.mesh_data = self._load_mesh(model)
        mesh_object = model.to_mesh_object()
        if model.add_to_scene:
            mesh_object.set_visible(True)
        self.object_importer.register(
            mesh_object,
            parent=mesh_root,
            add_to_scene=model.add_to_scene,
        )
        self._show_mesh(mesh_object)
        return mesh_object

    def create_context_menu(self, node, parent: Optional[QWidget] = None):
        """Create actions appropriate for a tree node."""
        options = []
        if node is mesh_root:
            options.append(("Import Mesh", self.import_mesh))
        elif isinstance(node.node_object, MeshObject):
            options.append(("Show in scene", lambda: self.show_mesh(node.node_object)))
            options.append(("Delete", lambda: self.delete_mesh(node.node_object)))
        return create_dropdown_menu(options, parent)

    def show_mesh(self, mesh_object: MeshObject):
        """Add a mesh to the active scene pipeline if it is not already loaded."""
        mesh_object.set_visible(True)
        self.object_importer.register(mesh_object, parent=mesh_root)
        return mesh_object

    def delete_mesh(self, mesh_object: MeshObject):
        """Delete a mesh from the application while preserving no references."""
        self.object_importer.remove(mesh_object)
        tree_model = self.tree_view.model()
        if isinstance(tree_model, TreeModel):
            tree_model.refresh()
        return mesh_object

    @staticmethod
    def _load_mesh(model):
        """Load and apply the dialog's transforms to a PyVista dataset."""
        mesh = pv.read(model.source_path)
        mesh.scale(model.scale, inplace=True)
        mesh.rotate_x(model.rotation[0], inplace=True)
        mesh.rotate_y(model.rotation[1], inplace=True)
        mesh.rotate_z(model.rotation[2], inplace=True)
        mesh.translate(model.offset, inplace=True)
        return mesh

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
