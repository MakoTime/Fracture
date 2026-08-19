from PySide6.QtWidgets import QHeaderView

from components.tree import TreeManager, TreeModel
from components.tree.roots import root_objects
from menu import setup_menu
from application.importers import ObjectImporterModel


class ProjectController:
    """Compose the project window's shared models and feature controllers."""

    def __init__(self, window):
        self.window = window
        self.tree_manager = TreeManager()
        self.table_manager = window.tableView.table_manager
        self.table_model = window.tableView.table_model
        self.object_importer = None
        self.controllers = []

    def setup(self):
        """Connect the loaded widgets and initialize project features."""
        self.tree_manager.root_nodes = root_objects.get_nodes()
        self.window.table_manager = self.table_manager
        self.window.tree_manager = self.tree_manager
        self.window.treeWidget.setHeaderHidden(True)
        self.window.treeWidget.setModel(TreeModel(root_objects.get_nodes()))
        self.window.tableView.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.window.tableView.clicked.connect(self.table_model.handle_click)
        self.window.scene_viewer = self.window.centralWidget()
        self.object_importer = ObjectImporterModel(
            table_model=self.table_model,
            tree_manager=self.tree_manager,
            scene_viewer=self.window.scene_viewer,
        )
        self.window.object_importer = self.object_importer
        self.controllers.extend(
            self.object_importer.bind_registered_features(
                tree_view=self.window.treeWidget,
                parent=self.window,
            )
        )
        setup_menu(self.window)
        return self.window
