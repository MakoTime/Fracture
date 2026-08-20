from types import SimpleNamespace

import pyvista as pv
from PySide6.QtGui import QColor, QImage

from application.importers import ObjectImporterModel
from application.project_serializer import ProjectSerializer
from application.project_version import upgrade_project_data
from components.table import TableManager, TableModel
from components.tree import TreeManager, TreeModel
from components.tree.roots import mesh_root, root_objects
from dialog.mesh_import.model import MeshImportModel
from engine.block_objects import MeshBlockObject
from objects.mesh_object import MeshObject


class FakeScene:
    def __init__(self):
        self.objects = []
        self.scene_model = SimpleNamespace(objects=self.objects)

    def add_object(self, object_base):
        self.objects.append(object_base)

    def remove_object(self, object_base):
        if object_base not in self.objects:
            return False
        self.objects.remove(object_base)
        return True

    def set_object_visibility(self, object_base, visible):
        pass

    def clear_scene(self):
        self.objects.clear()


def test_project_round_trip_saves_mesh_block_and_scene_state(tmp_path):
    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    mesh = MeshObject(
        name="Saved terrain",
        block_object=MeshBlockObject(mesh_data=pv.Sphere()),
        comments="round trip",
        guid="saved-guid",
        visible=False,
    )
    importer.register(mesh, parent=mesh_root, add_to_scene=True)
    mesh.set_visible(False)

    serializer = ProjectSerializer()
    project_file = serializer.save(tmp_path, table_model, scene)

    assert project_file.name == "project.json"
    assert (tmp_path / "block_data" / "saved-guid.vtp").exists()
    saved_data = project_file.read_text(encoding="utf-8")
    assert "low_threshold" not in saved_data
    assert "high_threshold" not in saved_data
    assert "vertical_scale" not in saved_data
    assert "source_path" not in saved_data
    assert "scale" not in saved_data
    assert "rotation" not in saved_data
    assert "offset" not in saved_data

    serializer.load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = mesh_root.children[0].node_object
    assert restored.guid == "saved-guid"
    assert restored.comments == "round trip"
    assert restored.mesh_block_object.name == "Saved terrain"
    assert restored.mesh_block_object.guid == "saved-guid"
    assert restored.mesh_block_object.comments == "round trip"
    assert restored.source_path == ""
    assert restored.scale == (1.0, 1.0, 1.0)
    assert restored.node.parent is mesh_root
    assert restored in scene.objects
    assert restored.visible is False
    assert restored.mesh_data.n_points == mesh.mesh_data.n_points


def test_project_round_trip_saves_structured_elevation_block(qapp, tmp_path):
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.fill(QColor(128, 128, 128))
    source_path = tmp_path / "elevation.png"
    assert image.save(str(source_path))
    model = MeshImportModel(source_path=str(source_path))
    block = model.to_mesh_import_task().process()

    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    mesh = model.to_mesh_object(block)
    importer.register(mesh, parent=mesh_root, add_to_scene=False)

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    assert (tmp_path / "block_data" / f"{mesh.guid}.vts").exists()
    mesh_root.children.clear()
    root_objects.nodes[:] = [mesh_root]

    ProjectSerializer().load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = mesh_root.children[0].node_object
    assert restored.mesh_block_object.mesh_data is None
    assert restored.mesh_data.n_points == 4


def test_processed_block_can_be_persisted_and_released(tmp_path):
    block = MeshBlockObject(mesh_data=pv.Sphere())
    output = block.serialise_to_directory(tmp_path / "block_data")

    assert output.exists()
    block.release()
    assert block.mesh_data is None
    assert block.scene_data.n_points > 0


def test_project_version_upgrades_legacy_metadata():
    upgraded = upgrade_project_data({"format": 1, "objects": []})

    assert upgraded == {"version": 1, "objects": []}


def test_project_version_rejects_newer_metadata():
    try:
        upgrade_project_data({"version": 2, "objects": []})
    except ValueError as error:
        assert "newer" in str(error)
    else:
        raise AssertionError("Newer project versions must be rejected")
