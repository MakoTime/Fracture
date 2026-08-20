import json
from types import SimpleNamespace

from application.file_window import (
    ProjectListModel,
    ProjectMetadataModel,
    RecentProjectStore,
    ProjectEntry,
    _new_project_file,
)
from application.project_controller import ProjectController
from application.project_serializer import ProjectSerializer
from components.table import TableManager, TableModel
from components.world_state import WorldStateModel
from main import load_application_window, load_file_window


def test_recent_project_store_remembers_newest_project(tmp_path):
    storage = RecentProjectStore(tmp_path / "recent.json")
    first = tmp_path / "first" / "project.json"
    second = tmp_path / "second" / "project.json"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text(json.dumps({"version": 1, "objects": []}))
    second.write_text(json.dumps({"version": 1, "objects": []}))

    storage.remember(first)
    storage.remember(second)

    entries = storage.load()
    assert [entry.path for entry in entries] == [second, first]
    assert entries[0].last_opened


def test_project_list_model_exposes_project_columns(tmp_path):
    project = tmp_path / "project" / "project.json"
    project.parent.mkdir()
    project.write_text("{}")
    model = ProjectListModel([])
    model.entries = [
        type("Entry", (), {"name": "Example", "path": project, "last_opened": ""})()
    ]

    assert model.columnCount() == 3
    assert model.data(model.index(0, 0)) == "Example"
    assert model.data(model.index(0, 1)) == str(project.parent)


def test_project_name_uses_custom_filename_instead_of_parent_folder(tmp_path):
    project = tmp_path / "MyProject.json"

    assert ProjectEntry(project).name == "MyProject"
    assert ProjectEntry(tmp_path / "Folder" / "project.json").name == "Folder"


def test_new_project_selection_creates_project_folder(tmp_path):
    assert _new_project_file(tmp_path / "MyProject") == (
        tmp_path / "MyProject" / "project.json"
    )
    assert _new_project_file(tmp_path / "MyProject.json") == (
        tmp_path / "MyProject" / "project.json"
    )


def test_world_state_model_summarizes_scene_state():
    model = WorldStateModel()
    model.refresh()

    assert model.rowCount() == 3
    assert model.data(model.index(0, 0)) == "Mesh objects"
    assert model.data(model.index(0, 1)) == "0"


def test_metadata_model_replaces_rows(qapp):
    model = ProjectMetadataModel()
    model.set_metadata([("Version", "1"), ("Objects", "2")])

    assert model.rowCount() == 2
    assert model.data(model.index(1, 1)) == "2"


def test_file_window_loads_from_designer_ui(qapp):
    file_window = load_file_window()

    assert file_window.window.objectName() == "FileWindow"
    assert file_window.window.newButton.text() == "New project..."
    assert file_window.window.recentProjectsTable.model().columnCount() == 3
    assert file_window.window.metadataTable.model().columnCount() == 2
    file_window.window.close()


def test_application_window_starts_on_project_tab(qapp):
    window = load_application_window()

    tabs = window.centralWidget()
    assert tabs.count() == 1
    assert tabs.tabText(0) == "Open Project"
    assert tabs.currentWidget().objectName() == "FileWindow"

    window.close()


def test_new_project_creates_empty_saved_project(qapp, tmp_path):
    project_file = tmp_path / "new-project" / "project.json"
    table_model = TableModel(TableManager())
    controller = ProjectController.__new__(ProjectController)
    controller.project_serializer = ProjectSerializer()
    controller.table_model = table_model
    controller.window = SimpleNamespace(scene_viewer=SimpleNamespace(
        scene_model=SimpleNamespace(objects=[]),
    ))
    controller.object_importer = SimpleNamespace()

    saved_file = controller.create_project(project_file)

    data = json.loads(saved_file.read_text(encoding="utf-8"))
    assert saved_file == project_file
    assert data["objects"] == []
    assert "version" in data
    assert (project_file.parent / "block_data").is_dir()
