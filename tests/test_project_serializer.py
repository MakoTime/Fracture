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
    island_root,
    mesh_root,
    root_objects,
    transform_root,
    world_config,
)
from dialog.perlin_noise_transform import PerlinNoiseTransformModel
from dialog.mesh_import.model import MeshImportModel
from dialog.mesh_filter import MeshFilterModel
from dialog.mesh_generate import MeshGenerateModel
from engine import EngineTaskModel, TaskStatus
from engine.block_tasks import GeneratedMeshTask, MeshFilterTask, PerlinNoiseTransformTask
from objects.generated_mesh import GeneratedMesh
from engine.block_objects import GeneratedMeshBlockObject, MeshBlockObject
from engine.block_objects import BlockObject
from engine.block_objects import PerlinNoiseTransformBlockObject
from engine.block_objects import ColourmapBlockObject
from engine.block_objects import IslandBlockObject, WorldConfigBlockObject
from objects.colourmap import ColourmapObject
from objects.mesh_object import MeshObject
from objects.island import Island


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


class MockBlockObject(BlockObject):
    def prepare(self):
        return self

    def process(self, prepared, progress_callback=None):
        return self

    def serialise(self, path):
        return path

    def serialise_to_directory(self, directory):
        return directory


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
    mesh.set_colourmap_scope("global")
    importer.register(mesh, parent=mesh_root, add_to_scene=True)
    mesh.set_visible(False)

    serializer = ProjectSerializer()
    original_centre = world_config.centre
    world_config.update_configuration(centre=(9.0, 8.0, 7.0))
    project_file = serializer.save(tmp_path, table_model, scene)

    saved_data = json.loads(project_file.read_text(encoding="utf-8"))
    assert saved_data["world_config"]["centre"] == [9.0, 8.0, 7.0]
    saved_mesh = next(
        item for item in saved_data["objects"] if item["guid"] == "saved-guid"
    )
    assert saved_mesh["colourmap_scope"] == "global"
    world_config.update_configuration(centre=(1.0, 2.0, 3.0))

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
    assert restored.mesh_block_object.colourmap_scope == "global"
    assert restored.source_path == ""
    assert restored.scale == (1.0, 1.0, 1.0)
    assert restored.node.parent is mesh_root
    assert restored in scene.objects
    assert restored.visible is False
    assert restored.mesh_data.n_points == mesh.mesh_data.n_points
    assert world_config.centre == (9.0, 8.0, 7.0)
    world_config.update_configuration(centre=original_centre)


def test_loaded_block_relationship_propagates_child_changes_and_invalidation():
    saved_parent = MockBlockObject(name="Parent", guid="parent-guid")
    saved_child = MockBlockObject(name="Child", guid="child-guid")
    saved_parent.add_child_block_object(saved_child)
    saved_item = {
        "guid": saved_parent.guid,
        "child_references": ProjectSerializer._child_references(saved_parent),
    }

    loaded_parent = MockBlockObject(name="Parent", guid="parent-guid")
    loaded_child = MockBlockObject(name="Child", guid="child-guid")
    loaded = {
        loaded_parent.guid: SimpleNamespace(block_object=loaded_parent),
        loaded_child.guid: SimpleNamespace(block_object=loaded_child),
    }

    ProjectSerializer._restore_block_relationships([saved_item], loaded)

    assert loaded_parent.child_block_objects == (loaded_child,)
    loaded_child.mark_changed()
    assert not loaded_parent.is_valid()
    loaded_parent.validate()
    loaded_child.validate()
    loaded_child.invalidate(force=True)
    assert not loaded_parent.is_valid()


def test_project_round_trip_preserves_island_orbital_configuration(tmp_path):
    table_model = TableModel(TableManager())
    tree_manager = TreeManager()
    tree_manager.root_nodes = root_objects.get_nodes()
    scene = FakeScene()
    importer = ObjectImporterModel(table_model, tree_manager, scene)
    source = MeshObject(
        name="Island source",
        block_object=MeshBlockObject(mesh_data=pv.Sphere()),
        guid="island-source-guid",
    )
    island_block = IslandBlockObject(
        mesh_block=source.block_object,
        world_config=world_config.block_object,
        core_offset=5.0,
        orbit_normal=(0.0, 2.0, 0.0),
        orbit_angle=18.0,
        curve_mesh=True,
        mesh_data=pv.Sphere(radius=1.0),
        guid="island-guid",
    )
    island = Island(
        name="Orbiting island",
        block_object=island_block,
        guid="island-guid",
    )
    importer.register(source, parent=mesh_root, add_to_scene=False)
    importer.register(island, parent=island_root, add_to_scene=True)

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    saved = json.loads(project_file.read_text(encoding="utf-8"))
    item = next(item for item in saved["objects"] if item["type"] == "island")
    assert item["core_offset"] == 5.0
    assert item["orbit_normal"] == [0.0, 1.0, 0.0]
    assert item["orbit_angle"] == 18.0
    assert item["curve_mesh"] is True

    ProjectSerializer().load(
        project_file,
        importer,
        TreeModel(root_objects.get_nodes()),
        table_model,
        scene,
    )

    restored = island_root.children[0].node_object
    assert restored.block_object.core_offset == 5.0
    assert restored.block_object.orbit_normal == (0.0, 1.0, 0.0)
    assert restored.block_object.orbit_angle == 18.0
    assert restored.block_object.curve_mesh is True
    assert restored.block_object.mesh_block is not None
    assert restored.block_object.world_config is world_config.block_object
    assert restored.show_in_scene is True
    restored_source = mesh_root.children[0].node_object
    restored.destroy()
    restored_source.destroy()


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
        application_mode="noise_mask",
        penetration=6,
    ).to_object()
    importer.register(transform, parent=transform_root, add_to_scene=False)

    project_file = ProjectSerializer().save(tmp_path, table_model, scene)
    saved = json.loads(project_file.read_text(encoding="utf-8"))
    item = saved["objects"][0]
    assert item["manual_sampling"] is True
    assert item["preset"] == "Sin wave"
    assert item["preset_options"]["phase"] == 90.0
    assert item["application_mode"] == "noise_mask"
    assert item["penetration"] == 6

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
    assert restored.block_object.application_mode == "noise_mask"
    assert restored.block_object.penetration == 6


def test_project_round_trip_saves_structured_elevation_block(qapp, tmp_path):
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.fill(QColor(128, 128, 128))
    source_path = tmp_path / "elevation.png"
    assert image.save(str(source_path))
    model = MeshImportModel(source_path=str(source_path))
    task = model.to_mesh_import_task()
    block = task.execute(task.prepare())

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


# def test_filtered_mesh_round_trip_queues_perlin_and_parent_tasks_after_change(
#     qapp, tmp_path
# ):
#     table_model = TableModel(TableManager())
#     tree_manager = TreeManager()
#     tree_manager.root_nodes = root_objects.get_nodes()
#     scene = FakeScene()
#     importer = ObjectImporterModel(table_model, tree_manager, scene)
#     transform = PerlinNoiseTransformModel(name="Filter noise").to_object()
#     source = GeneratedMesh(
#         name="Source",
#         grid_data=[[[1.0, 1.0], [1.0, 1.0]]],
#         mesh_data=pv.Sphere(),
#         guid="filter-source",
#     )
#     filter_model = MeshFilterModel.from_mesh(source)
#     filter_model.perlin_noise_transform = transform
#     filter_model.noise_enabled = True
#     filtered = filter_model.generate()
#     importer.register(source, parent=mesh_root, add_to_scene=False)
#     importer.register(filtered, parent=mesh_root, add_to_scene=False)
#     importer.register(transform, parent=transform_root, add_to_scene=False)

#     project_file = ProjectSerializer().save(tmp_path, table_model, scene)
#     saved = json.loads(project_file.read_text(encoding="utf-8"))
#     filtered_item = next(
#         item for item in saved["objects"] if item["guid"] == filtered.guid
#     )
#     assert {reference["guid"] for reference in filtered_item["child_references"]} == {
#         transform.guid,
#         source.guid,
#     }
#     ProjectSerializer().load(
#         project_file,
#         importer,
#         TreeModel(root_objects.get_nodes()),
#         table_model,
#         scene,
#     )

#     restored = next(
#         node.node_object
#         for node in mesh_root.children
#         if node.node_object.name == filtered.name
#     )
#     restored_source = next(
#         node.node_object
#         for node in mesh_root.children
#         if node.node_object.guid == source.guid
#     )
#     restored_transform = transform_root.children[0].node_object
#     assert restored_transform.block_object in restored.block_object.child_block_objects

#     runner = EngineTaskModel()
#     source_model = MeshGenerateModel(
#         name=restored_source.name,
#         grid_size=restored_source.grid_data.shape,
#     )
#     runner.enqueue_block_task(
#         "Regenerate source",
#         GeneratedMeshTask(source_model, restored_source.block_object),
#     )
#     runner.enqueue_block_task(
#         "Generate filter noise",
#         PerlinNoiseTransformTask(restored_transform.block_object),
#     )
#     runner.enqueue_block_task(
#         "Filter mesh",
#         MeshFilterTask(
#             restored_source.block_object,
#             restored_transform.block_object,
#             0.25,
#             0.75,
#             1,
#             block_object=restored.block_object,
#         ),
#     )
#     assert runner.wait_for_done()
#     qapp.processEvents()

#     runner.pause()
#     restored_transform.block_object.update_configuration(seed=1)
#     assert runner.tasks[0].status is TaskStatus.QUEUED
#     assert runner._block_tasks[restored.block_object.guid]["waiting_for_children"]

#     runner.play()
#     assert runner.wait_for_done()
#     qapp.processEvents()
#     assert restored.block_object.is_valid()


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
    assert mesh_item["child_references"] == []
    assert mesh_item["transform_reference"] == transform.guid

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
    assert restored.block_object.child_block_objects == (
        restored_transform.block_object,
    )
    restored.block_object.validate()
    restored_transform.block_object.validate()
    restored_transform.block_object.invalidate(force=True)
    assert not restored.block_object.is_valid()


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
    assert restored.block_object.child_block_objects == (
        restored_transform.block_object,
    )
    restored.block_object.validate()
    restored_transform.block_object.validate()
    restored_transform.block_object.invalidate(force=True)
    assert not restored.block_object.is_valid()


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
