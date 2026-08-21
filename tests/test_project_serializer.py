import json
from types import SimpleNamespace

import pyvista as pv
from PySide6.QtGui import QColor, QImage

from application.importers import ObjectImporterModel
from application.project_serializer import ProjectSerializer
from application.project_version import upgrade_project_data
from components.table import TableManager, TableModel
from components.tree import TreeManager, TreeModel
from components.tree.roots import (
    colourmap_root,
    mesh_root,
    root_objects,
    transform_root,
)
from dialog.perlin_noise_transform import PerlinNoiseTransformModel
from dialog.mesh_import.model import MeshImportModel
from objects.generated_mesh import GeneratedMesh
from engine.block_objects import GeneratedMeshBlockObject, MeshBlockObject
from engine.block_objects import PerlinNoiseTransformBlockObject
from engine.block_objects import ColourmapBlockObject
from objects.colourmap import ColourmapObject
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


def test_project_round_trip_preserves_perlin_editor_schema(tmp_path):
    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    transform = PerlinNoiseTransformModel(
        name="Manual wave",
        frequencies=(2, 4, 8),
        amplitudes=(1.0, 0.5, 0.25),
        curve_mode="bezier",
        curve_points=((0.0, 0.0), (0.5, 1.0), (1.0, 0.0)),
        sample_count=17,
        manual_sampling=True,
        preset="Sin wave",
        preset_options={"phase": 90.0, "amplitude": 0.75},
    ).to_object()
    importer.register(transform, parent=transform_root, add_to_scene=False)

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    saved = json.loads(project_file.read_text(encoding="utf-8"))
    item = saved["objects"][0]
    assert item["manual_sampling"] is True
    assert item["preset"] == "Sin wave"
    assert item["preset_options"]["phase"] == 90.0

    ProjectSerializer().load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = transform_root.children[0].node_object
    assert restored.guid == transform.guid
    assert restored.block_object.sample_count == 17
    assert restored.block_object.manual_sampling is True
    assert restored.block_object.preset == "Sin wave"
    assert restored.block_object.preset_options["phase"] == 90.0


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


def test_generated_mesh_round_trip_preserves_grid_data(tmp_path):
    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    mesh = GeneratedMesh(
        name="Generated grid",
        grid_data=[[[0.25, 0.0], [0.75, 1.0]]],
        mesh_data=pv.PolyData(),
        guid="generated-guid",
    )
    importer.register(mesh, parent=mesh_root, add_to_scene=False)

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    assert (tmp_path / "block_data" / "generated-guid.grid.npy").exists()

    ProjectSerializer().load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = mesh_root.children[0].node_object
    assert isinstance(restored, GeneratedMesh)
    assert isinstance(restored.block_object, GeneratedMeshBlockObject)
    assert restored.grid_data.tolist() == [[[0.25, 0.0], [0.75, 1.0]]]


def test_project_round_trip_restores_block_child_references(tmp_path):
    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    transform = PerlinNoiseTransformModel(name="Saved noise").to_object()
    block = GeneratedMeshBlockObject(
        mesh_data=pv.Sphere(),
        grid_data=[[[1.0]]],
        perlin_noise_transform=transform.block_object,
    )
    mesh = GeneratedMesh(
        name="Saved generated mesh",
        block_object=block,
        guid="generated-with-transform",
    )
    importer.register(mesh, parent=mesh_root, add_to_scene=False)
    importer.register(transform, parent=transform_root, add_to_scene=False)
    mesh.node.set_block_child_objects((transform,))

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    saved = json.loads(project_file.read_text(encoding="utf-8"))
    assert [item["type"] for item in saved["objects"]] == [
        "generated_mesh",
        "perlin_noise_transform",
    ]
    mesh_item = next(
        item for item in saved["objects"] if item["guid"] == mesh.guid
    )
    assert mesh_item["child_references"] == [
        {"guid": transform.guid, "dependent": True}
    ]

    ProjectSerializer().load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = mesh_root.children[0].node_object
    restored_transform = transform_root.children[0].node_object
    assert isinstance(restored.block_object, GeneratedMeshBlockObject)
    assert isinstance(restored_transform.block_object, PerlinNoiseTransformBlockObject)
    assert restored.block_object.perlin_noise_transform is restored_transform.block_object
    assert restored.block_object.child_block_objects == (restored_transform.block_object,)
    assert restored.block_object._child_dependencies[restored_transform.block_object]


def test_project_round_trip_restores_colourmap_noise_transform(tmp_path):
    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    transform = PerlinNoiseTransformModel(name="Colour noise").to_object()
    colourmap = ColourmapObject(
        name="Terrain palette",
        block_object=ColourmapBlockObject(
            perlin_noise_transform=transform.block_object,
            noise_enabled=True,
        ),
    )
    importer.register(transform, parent=transform_root, add_to_scene=False)
    importer.register(colourmap, parent=colourmap_root, add_to_scene=False)

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    ProjectSerializer().load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = colourmap_root.children[0].node_object
    restored_transform = transform_root.children[0].node_object
    assert isinstance(restored, ColourmapObject)
    assert restored.block_object.noise_enabled is True
    assert (
        restored.block_object.perlin_noise_transform
        is restored_transform.block_object
    )
    assert restored_transform.block_object in restored.block_object.child_block_objects
    assert restored.block_object._child_dependencies[restored_transform.block_object] is False


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
