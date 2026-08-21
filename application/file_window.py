from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyvista as pv
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel

from application.project_version import upgrade_project_data
from objects.mesh_object import MeshObject
from engine.block_objects import MeshBlockObject


@dataclass
class ProjectEntry:
    path: Path
    last_opened: str = ""

    @property
    def name(self) -> str:
        return _project_name(self.path)


def _project_name(path: Path) -> str:
    """Use a custom project filename, or the folder for project.json files."""
    if path.name.lower() == "project.json":
        return path.parent.name or path.stem
    return path.stem or path.parent.name


def _new_project_file(selection: str | Path) -> Path:
    """Convert a new-project name into ``ProjectFolder/project.json``."""
    project_directory = Path(selection)
    if project_directory.suffix.lower() == ".json":
        project_directory = project_directory.with_suffix("")
    return project_directory / "project.json"


class RecentProjectStore:
    """Persist recently opened project files outside the project itself."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or (
            Path.home() / ".rainfall" / "recent_projects.json"
        )

    def load(self) -> list[ProjectEntry]:
        if not self.storage_path.exists():
            return []
        try:
            values = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        entries = []
        for value in values if isinstance(values, list) else []:
            path = Path(value.get("path", ""))
            if path.is_file():
                entries.append(ProjectEntry(path, value.get("last_opened", "")))
        return entries

    def remember(self, path: Path) -> None:
        entries = [entry for entry in self.load() if entry.path != path]
        entries.insert(
            0,
            ProjectEntry(
                path=path,
                last_opened=datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"path": str(entry.path), "last_opened": entry.last_opened}
            for entry in entries[:20]
        ]
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class ProjectListModel(QAbstractTableModel):
    headers = ["Project", "Location", "Last opened"]

    def __init__(self, entries: list[ProjectEntry]):
        super().__init__()
        self.entries = entries

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.entries)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        entry = self.entries[index.row()]
        values = (entry.name, str(entry.path.parent), _format_date(entry.last_opened))
        return values[index.column()]


def _format_date(value: str) -> str:
    if not value:
        return "Never"
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


class ProjectMetadataModel(QAbstractTableModel):
    headers = ["Property", "Value"]

    def __init__(self):
        super().__init__()
        self.rows: list[tuple[str, str]] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return self.rows[index.row()][index.column()]
        return None

    def set_metadata(self, rows: list[tuple[str, str]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class ProjectPreview(QLabel):
    """Render a lightweight image preview without creating a Qt VTK widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("No preview")
        self.setMinimumSize(320, 240)

    def clear_scene(self):
        self.clear()
        self.setText("No preview")

    def set_meshes(self, meshes: list[Any]):
        if not meshes:
            self.clear_scene()
            return
        plotter = pv.Plotter(off_screen=True, window_size=(640, 360))
        plotter.enable_3_lights()
        try:
            for mesh in meshes:
                if isinstance(mesh, pv.StructuredGrid):
                    mesh = mesh.extract_surface(
                        algorithm="dataset_surface",
                    ).compute_normals(
                        auto_orient_normals=True,
                        split_vertices=False,
                        inplace=False,
                    )
                plotter.add_mesh(mesh)
            plotter.reset_camera()
            image = plotter.screenshot(return_img=True)
        finally:
            plotter.close()
        height, width, channels = image.shape
        qimage = QImage(
            image.data,
            width,
            height,
            channels * width,
            QImage.Format.Format_RGB888,
        ).copy()
        self.setPixmap(QPixmap.fromImage(qimage))


class FileWindow:
    """Coordinate the project picker UI loaded from ``file_window.ui``."""

    def __init__(
        self,
        window,
        store: RecentProjectStore | None = None,
        on_project_opened=None,
        on_project_created=None,
    ):
        self.window = window
        self.store = store or RecentProjectStore()
        self.on_project_opened = on_project_opened
        self.on_project_created = on_project_created
        self.entries = self.store.load()
        self.selected_project: Path | None = None
        self.list_model = ProjectListModel(self.entries)
        self.metadata_model = ProjectMetadataModel()
        self.window.recentProjectsTable.setModel(self.list_model)
        self.window.metadataTable.setModel(self.metadata_model)
        self.window.recentProjectsTable.selectionModel().selectionChanged.connect(
            self._selection_changed
        )
        self.window.openButton.clicked.connect(self.open_selected)
        self.window.newButton.clicked.connect(self.new_project)
        self.window.browseButton.clicked.connect(self.browse_project)
        self.window.cancelButton.clicked.connect(self.window.reject)
        self.window.recentProjectsTable.doubleClicked.connect(
            lambda index: self.open_selected()
        )
        if self.entries:
            self.window.recentProjectsTable.selectRow(0)
        else:
            self._clear_preview()

    def _selection_changed(self, selected, _deselected):
        if not selected.indexes():
            return
        entry = self.entries[selected.indexes()[0].row()]
        self._show_project(entry.path, entry.last_opened)

    def _show_project(self, path: Path, last_opened: str = ""):
        try:
            data = upgrade_project_data(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError, TypeError) as error:
            self._clear_preview()
            self.window.previewTitle.setText("Unable to preview project")
            self.metadata_model.set_metadata([("Error", str(error))])
            return

        self.window.previewTitle.setText(_project_name(path))
        objects = data.get("objects", [])
        scene_objects = [item for item in objects if item.get("in_scene")]
        rows = [
            ("Path", str(path)),
            ("Last opened", _format_date(last_opened)),
            ("Version", str(data.get("version", "Unknown"))),
            ("Objects", str(len(objects))),
            ("Objects in scene", str(len(scene_objects))),
        ]
        self.metadata_model.set_metadata(rows)
        self._show_preview(path, objects)

    def _show_preview(self, project_path: Path, objects: list[dict[str, Any]]):
        self.window.projectPreview.clear_scene()
        self._preview_meshes = []
        for item in objects:
            if item.get("type") not in ("mesh", "generated_mesh"):
                continue
            if not item.get("in_scene", True):
                continue
            block_path = project_path.parent / item.get("block_data", "")
            if not block_path.is_file():
                continue
            if block_path.name.endswith(".colourmap.json"):
                continue
            block = MeshBlockObject.load(
                block_path,
                name=item.get("name", "Mesh"),
                guid=item.get("guid"),
                comments=item.get("comments", ""),
            )
            preview_object = MeshObject(
                name=block.name,
                block_object=block,
                visible=True,
                guid=block.guid,
                auto_register_root=False,
            )
            meshes = getattr(self, "_preview_meshes", [])
            meshes.append(preview_object.mesh_data)
            self._preview_meshes = meshes
        self.window.projectPreview.set_meshes(
            getattr(self, "_preview_meshes", [])
        )

    def _clear_preview(self):
        self._preview_meshes = []
        self.window.previewTitle.setText("Select a project")
        self.metadata_model.set_metadata([])
        self.window.projectPreview.clear_scene()

    def open_selected(self):
        index = self.window.recentProjectsTable.currentIndex()
        if not index.isValid():
            self.browse_project()
            return
        self.selected_project = self.entries[index.row()].path
        self.store.remember(self.selected_project)
        self._finish_open()

    def browse_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Open RainFall Project",
            str(Path.home()),
            "RainFall projects (project.json);;JSON files (*.json)",
        )
        if not path:
            return
        project_path = Path(path)
        self.store.remember(project_path)
        self.selected_project = project_path
        self._finish_open()

    def new_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self.window,
            "New RainFall Project",
            str(Path.home() / "project.json"),
            "RainFall projects (project.json);;JSON files (*.json)",
        )
        if not path:
            return
        project_path = _new_project_file(path)
        self.store.remember(project_path)
        self.selected_project = project_path
        if self.on_project_created:
            self.on_project_created(project_path)

    def _finish_open(self):
        if self.on_project_opened:
            self.on_project_opened(self.selected_project)
        else:
            self.window.accept()


def create_file_window(window):
    return FileWindow(window)
