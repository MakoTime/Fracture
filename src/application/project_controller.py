from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QHeaderView,
)

from src.application.importers import ObjectImporterModel
from src.application.importers.colourmap_controller import ColourmapController
from src.application.importers.island_controller import IslandController
from src.application.importers.transform_controller import TransformController
from src.application.importers.world_config_controller import WorldConfigController
from src.application.project_serializer import ProjectSerializer
from src.components.tree import TreeManager, TreeModel
from src.components.tree.roots import root_objects
from src.menu import setup_menu
from src.dialog.notify import create_notification


class ProjectController:
    """Compose the project window's shared models and feature controllers."""

    def __init__(self, window):
        self.window = window
        self.tree_manager = TreeManager()
        self.table_manager = window.tableView.table_manager
        self.table_model = window.tableView.table_model
        self.object_importer = None
        self.controllers = []
        self.project_serializer = ProjectSerializer()
        self.project_file = None
        self._project_loading = False

    def setup(self, menu_bar=None):
        """Connect the loaded widgets and initialize project features."""
        self.tree_manager.root_nodes = root_objects.get_nodes()
        self.window.table_manager = self.table_manager
        self.window.tree_manager = self.tree_manager
        self.window.treeWidget.setHeaderHidden(True)
        self.tree_model = TreeModel(
            root_objects.get_nodes(),
            duplicate_name_handler=self._resolve_duplicate_name,
        )
        self.window.treeWidget.setModel(self.tree_model)
        self.window.tableView.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self._configure_scene_splitters()
        self.window.tableView.clicked.connect(self.table_model.handle_click)
        self.window.workspace_tabs = self.window.workspaceTabs
        self.window.scene_viewer = self.window.sceneViewer
        self.window.engine_runner = self.window.engineRunner
        self._lock_scene_docks()
        self.window.worldStateView.set_scene_model(self.window.scene_viewer.scene_model)
        self.object_importer = ObjectImporterModel(
            table_model=self.table_model,
            tree_manager=self.tree_manager,
            scene_viewer=self.window.scene_viewer,
            tree_model=self.tree_model,
        )
        self.object_importer.set_project_save_callback(self._save_project_after_block)
        self.window.worldStateView.timer_controller = (
            self.object_importer.timer_controller
        )
        self.object_importer.engine_runner = self.window.engine_runner
        self.window.object_importer = self.object_importer
        self.controllers.extend(
            self.object_importer.bind_registered_features(
                tree_view=self.window.treeWidget,
                parent=self.window,
                engine_runner=self.window.engine_runner,
            )
        )
        self.controllers.append(
            TransformController(
                object_importer=self.object_importer,
                tree_view=self.window.treeWidget,
                parent=self.window,
                engine_runner=self.window.engineRunner,
            )
        )
        self.controllers.append(
            ColourmapController(
                object_importer=self.object_importer,
                tree_view=self.window.treeWidget,
                parent=self.window,
                engine_runner=self.window.engineRunner,
            )
        )
        self.controllers.append(
            WorldConfigController(
                tree_view=self.window.treeWidget,
                parent=self.window,
            )
        )
        self.controllers.append(
            IslandController(
                object_importer=self.object_importer,
                tree_view=self.window.treeWidget,
                parent=self.window,
                engine_runner=self.window.engineRunner,
            )
        )
        if menu_bar is None:
            setup_menu(self.window)
            self.window.save_action.triggered.connect(
                lambda checked=False: self.save_project()
            )
            self.window.save_as_action.triggered.connect(
                lambda checked=False: self.save_project_as()
            )
            self.window.open_action.triggered.connect(
                lambda checked=False: self.open_project()
            )
        return self.window

    def _resolve_duplicate_name(self, name, object_base):
        next_name = self.tree_model.next_name(name, exclude=object_base)
        dialog = create_notification(
            "Duplicate name",
            f"The name '{name}' is already in use.\n"
            f"Click OK to use '{next_name}' instead, or Cancel to revert.",
            parent=self.window,
            confirm=True,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return next_name

    def _configure_scene_splitters(self):
        """Set compact defaults while keeping all panels resizable."""
        navigation_splitter = self.window.treeDockSplitter
        navigation_splitter.setStretchFactor(0, 2)
        navigation_splitter.setStretchFactor(1, 1)

        main_splitter = self.window.sceneMainSplitter
        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 1)
        QTimer.singleShot(
            0, lambda: self._set_scene_splitter_sizes(navigation_splitter, (2, 1))
        )
        QTimer.singleShot(
            0, lambda: self._set_scene_splitter_sizes(main_splitter, (5, 1))
        )

    @staticmethod
    def _set_scene_splitter_sizes(splitter, ratio):
        total = splitter.width()
        if total <= 0:
            return
        first = round(total * ratio[0] / sum(ratio))
        splitter.setSizes([first, total - first])

    def _lock_scene_docks(self):
        """Keep Scene-tab panels embedded and resizable without controls."""
        dock_features = QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        for dock_name in (
            "treeDockWidget",
            "sceneDockWidget",
            "worldStateDockWidget",
        ):
            dock = self.window.findChild(QDockWidget, dock_name)
            if dock is not None:
                dock.setFeatures(dock_features)
                dock.setFloating(False)

    def save_project(self):
        """Save the current project to its active project file."""
        if self.project_file is None:
            return self.save_project_as()
        return self.project_serializer.save(
            self.project_file,
            self.table_model,
            self.window.scene_viewer,
        )

    def _save_project_after_block(self, block_object):
        """Save project metadata after an application-level block save."""
        del block_object
        if self._project_loading or self.project_file is None:
            return None
        return self.save_project()

    def save_project_as(self):
        """Save the current project to a newly selected metadata file."""
        dialog = QFileDialog(self.window, "Save Project As")
        dialog.setOption(
            QFileDialog.Option.DontUseNativeDialog,
            True,
        )
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setNameFilter("Fracture projects (project.json);;JSON files (*.json)")
        default_directory = (
            self.project_file.parent if self.project_file else Path.home()
        )
        default_name = self.project_file.name if self.project_file else "project.json"
        dialog.setDirectory(str(default_directory))
        dialog.selectFile(default_name)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        selected_files = dialog.selectedFiles()
        project_file = selected_files[0] if selected_files else ""
        if not project_file:
            return None
        saved_file = self.project_serializer.save(
            project_file,
            self.table_model,
            self.window.scene_viewer,
        )
        self.project_file = saved_file
        self._set_block_data_directory(saved_file)
        return saved_file

    def create_project(self, project_file):
        """Create an empty project and make it the active save target."""
        timer_controller = getattr(self.object_importer, "timer_controller", None)
        if timer_controller is not None:
            timer_controller.clear()
        self.project_serializer._clear_current_project(
            self.table_model,
            self.window.scene_viewer,
            getattr(self.window, "engine_runner", None),
            getattr(self, "tree_model", None),
        )
        saved_file = self.project_serializer.save(
            project_file,
            self.table_model,
            self.window.scene_viewer,
        )
        self.project_file = saved_file
        self._set_block_data_directory(saved_file)
        return saved_file

    def close_project(self, save=False):
        """Close the active project and release its registered work."""
        if save:
            self.save_project()
        timer_controller = getattr(self.object_importer, "timer_controller", None)
        if timer_controller is not None:
            timer_controller.clear()
        self.project_serializer._clear_current_project(
            self.table_model,
            self.window.scene_viewer,
            self.window.engine_runner,
            self.tree_model,
        )
        self.project_file = None

    def load_project(self, project_file):
        """Load a project and make its file the active save target."""
        self._project_loading = True
        try:
            self._set_block_data_directory(project_file)
            loaded = self.project_serializer.load(
                project_file,
                self.object_importer,
                self.tree_model,
                self.table_model,
                self.window.scene_viewer,
            )
        finally:
            self._project_loading = False
        for controller in self.controllers:
            if hasattr(controller, "bind_loaded_tasks"):
                controller.bind_loaded_tasks(loaded)
        self.project_file = Path(project_file)
        return loaded

    def _set_block_data_directory(self, project_file):
        self.object_importer.block_data_directory = (
            Path(project_file).parent / "block_data"
        )

    def choose_project_file(self):
        """Ask the user for a project file without loading it."""
        from PySide6.QtWidgets import QFileDialog

        project_file, _ = QFileDialog.getOpenFileName(
            self.window,
            "Open Project",
            filter="Fracture projects (project.json);;JSON files (*.json)",
        )
        return project_file

    def open_project(self):
        """Load a project JSON file and rebuild its registered objects."""
        project_file = self.choose_project_file()
        if not project_file:
            return None
        return self.load_project(project_file)
