import json

from application.file_window import (
    ProjectListModel,
    ProjectMetadataModel,
    RecentProjectStore,
)
from main import load_file_window


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


def test_metadata_model_replaces_rows(qapp):
    model = ProjectMetadataModel()
    model.set_metadata([("Version", "1"), ("Objects", "2")])

    assert model.rowCount() == 2
    assert model.data(model.index(1, 1)) == "2"


def test_file_window_loads_from_designer_ui(qapp):
    file_window = load_file_window()

    assert file_window.window.objectName() == "FileWindow"
    assert file_window.window.recentProjectsTable.model().columnCount() == 3
    assert file_window.window.metadataTable.model().columnCount() == 2
    file_window.window.close()
