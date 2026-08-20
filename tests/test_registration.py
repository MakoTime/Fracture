from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage

from components.table import TableManager, TableModel
from components.tree import TreeModel
from components.tree.roots import mesh_root, root_objects
from dialog.mesh_import.model import MeshImportModel
from dialog.mesh_edit.model import MeshEditModel
from engine.block_objects import MeshBlockObject
from engine.block_tasks import MeshImportTask
from objects.mesh_object import MeshObject
from application.importers import MeshImportController, ObjectImporterModel
from objects.object_base import ObjectBase


def test_bitmap_elevation_map_creates_structured_grid(qapp, tmp_path):
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.setPixelColor(0, 0, QColor(0, 0, 0))
    image.setPixelColor(1, 0, QColor(64, 64, 64))
    image.setPixelColor(0, 1, QColor(128, 128, 128))
    image.setPixelColor(1, 1, QColor(255, 255, 255))
    source_path = tmp_path / "elevation.png"
    assert image.save(str(source_path))

    model = MeshImportModel(source_path=str(source_path))
    mesh = MeshImportController._load_mesh(model)

    assert mesh.dimensions == (2, 2, 1)
    assert mesh.n_points == 4
    assert mesh.points[:, 2].tolist() == [0.0, 64.0, 128.0, 255.0]


def test_elevation_settings_threshold_and_scale_mesh(qapp, tmp_path):
    image = QImage(2, 1, QImage.Format.Format_RGB32)
    image.setPixelColor(0, 0, QColor(10, 10, 10))
    image.setPixelColor(1, 0, QColor(200, 200, 200))
    source_path = tmp_path / "thresholded.png"
    assert image.save(str(source_path))

    model = MeshImportModel(
        source_path=str(source_path),
        low_threshold=50,
        high_threshold=100,
        vertical_scale=2,
    )
    mesh = MeshImportController._load_mesh(model)

    assert mesh.points[:, 2].tolist() == [100.0, 200.0]


def test_mesh_root_menu_separates_import_types(qapp):
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )

    menu = controller.create_context_menu(mesh_root)

    assert [action.text() for action in menu.actions()] == [
        "Import mesh from 3D object",
        "Import Mesh from elevation data",
    ]


def test_mesh_object_menu_includes_edit_action(qapp):
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )
    mesh_object = MeshImportModel(mesh_data=object()).to_mesh_object()

    menu = controller.create_context_menu(mesh_object.node)

    assert [action.text() for action in menu.actions()] == [
        "Edit Mesh",
        "Show in scene",
        "Delete",
    ]


def test_mesh_edit_model_updates_existing_mesh(qapp):
    mesh_object = MeshImportModel(
        name="Original",
        comments="old",
        mesh_data=object(),
    ).to_mesh_object()
    model = MeshEditModel.from_mesh_object(mesh_object)
    model.name = "Edited"
    model.comments = "new"
    model.scale = (2.0, 2.0, 2.0)

    assert model.apply() is mesh_object
    assert mesh_object.name == "Edited"
    assert mesh_object.comments == "new"
    assert mesh_object.scale == (2.0, 2.0, 2.0)
    assert mesh_object.node.name == "Edited"


def test_object_base_registers_as_global_root_by_default(qapp):
    object_base = ObjectBase("Root Object")

    assert object_base.node in root_objects.get_nodes()
    assert object_base.node.parent is None


def test_mesh_import_creates_mesh_object_as_child_only(qapp):
    mesh_object = MeshImportModel(
        name="Imported Mesh",
        guid="mesh-guid",
        comments="test mesh",
        mesh_data=object(),
    ).to_mesh_object()

    mesh_root.add_child(mesh_object.node)

    assert isinstance(mesh_object, MeshObject)
    assert mesh_object.node not in root_objects.get_nodes()
    assert mesh_object.node.parent is mesh_root
    assert mesh_root.children == [mesh_object.node]
    assert mesh_object.guid == "mesh-guid"
    assert mesh_object.visible is False
    assert mesh_object.comments == "test mesh"
    assert mesh_object.metadata["comments"] == "test mesh"
    assert isinstance(mesh_object.mesh_block_object, MeshBlockObject)
    assert mesh_object.mesh_block_object.mesh_data is mesh_object.mesh_data


def test_mesh_import_block_is_a_factory():
    import_task = MeshImportTask(
        MeshImportModel(name="Imported Mesh", guid="mesh-guid")
    )

    assert not isinstance(import_task, MeshBlockObject)


def test_tree_and_table_read_mesh_identity_from_block(qapp):
    table_manager = TableManager()
    table_model = TableModel(table_manager)
    mesh_object = MeshImportModel(
        name="Initial name",
        guid="initial-guid",
        mesh_data=object(),
    ).to_mesh_object()
    mesh_root.add_child(mesh_object.node)
    mesh_object.add_to_table(table_manager)
    tree_model = TreeModel(root_objects.get_nodes())

    mesh_object.block_object.name = "Block name"
    mesh_object.block_object.guid = "block-guid"

    root_index = tree_model.index(root_objects.get_nodes().index(mesh_root), 0)
    mesh_index = tree_model.index(0, 0, root_index)
    assert tree_model.data(mesh_index, Qt.DisplayRole) == "Block name"
    assert table_model.data(
        table_model.index(0, table_model.NAME),
        Qt.DisplayRole,
    ) == "Block name"
    assert mesh_object.name == "Block name"
    assert mesh_object.guid == "block-guid"


def test_object_base_registers_table_data(qapp):
    table_manager = TableManager()
    object_base = ObjectBase("Table Object")

    object_base.add_to_table(table_manager)

    assert table_manager.get_data() == [object_base.row_data]
    assert table_manager.get_data()[0].name == "Table Object"


def test_table_model_exposes_rows_added_after_view_creation(qapp):
    table_manager = TableManager()
    table_model = TableModel(table_manager)
    object_base = ObjectBase("Live Row")

    table_model.add_row(object_base.row_data)

    assert table_model.rowCount() == 1
    assert table_model.data(
        table_model.index(0, table_model.NAME),
        Qt.DisplayRole,
    ) == "Live Row"


def test_table_visibility_controls_scene_actor(qapp):
    class FakeScene:
        def __init__(self):
            self.visibility_changes = []

        def add_object(self, object_base):
            pass

        def set_object_visibility(self, object_base, visible):
            self.visibility_changes.append((object_base, visible))

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    object_base = ObjectBase("Visible Row")
    scene = FakeScene()
    object_base.add_to_scene(scene)
    table_model.add_row(object_base.row_data)

    visible_index = table_model.index(0, table_model.VISIBLE)
    assert table_model.setData(visible_index, Qt.CheckState.Unchecked, Qt.CheckStateRole)
    assert object_base.visible is False
    assert scene.visibility_changes == [(object_base, False)]

    assert table_model.setData(visible_index, 2, Qt.CheckStateRole)
    assert object_base.visible is True
    assert scene.visibility_changes == [
        (object_base, False),
        (object_base, True),
    ]


def test_table_remove_unloads_object_but_keeps_tree_node(qapp):
    class FakeScene:
        def __init__(self):
            self.objects = []
            self.scene_model = SimpleNamespace(objects=self.objects)

        def add_object(self, object_base):
            self.objects.append(object_base)

        def remove_object(self, object_base):
            self.objects.remove(object_base)
            return True

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    object_base = ObjectBase("Removable")
    scene = FakeScene()
    object_base.add_to_scene(scene)
    object_base.add_to_table(table_manager)
    assert scene.objects == [object_base]

    assert table_model.remove_row(0) is True
    assert table_model.rowCount() == 0
    assert scene.objects == []
    assert object_base.node in root_objects.get_nodes()


def test_show_mesh_restores_scene_and_table_pipeline(qapp):
    class FakeScene:
        def __init__(self):
            self.objects = []
            self.scene_model = SimpleNamespace(objects=self.objects)

        def add_object(self, object_base):
            self.objects.append(object_base)

        def remove_object(self, object_base):
            self.objects.remove(object_base)
            return True

        def set_object_visibility(self, object_base, visible):
            pass

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    scene = FakeScene()
    controller = MeshImportController(
        object_importer=ObjectImporterModel(
            table_model=table_model,
            tree_manager=SimpleNamespace(),
            scene_viewer=scene,
        ),
        tree_view=SimpleNamespace(),
    )
    mesh_object = MeshObject("Deferred Mesh", mesh_data=object())

    controller.show_mesh(mesh_object)

    assert scene.objects == [mesh_object]
    assert table_manager.get_data() == [mesh_object.row_data]
    assert mesh_object.visible is True


def test_delete_mesh_removes_scene_table_and_tree_membership(qapp):
    class FakeScene:
        def __init__(self):
            self.objects = []
            self.scene_model = SimpleNamespace(objects=self.objects)

        def add_object(self, object_base):
            self.objects.append(object_base)

        def remove_object(self, object_base):
            self.objects.remove(object_base)
            return True

        def set_object_visibility(self, object_base, visible):
            pass

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    scene = FakeScene()
    mesh_object = MeshObject("Delete Me", mesh_data=object())
    mesh_root.add_child(mesh_object.node)
    mesh_object.add_to_scene(scene)
    table_model.add_row(mesh_object.row_data)
    tree_model = TreeModel([mesh_root])
    controller = MeshImportController(
        object_importer=ObjectImporterModel(
            table_model=table_model,
            tree_manager=SimpleNamespace(),
            scene_viewer=scene,
        ),
        tree_view=SimpleNamespace(model=lambda: tree_model),
    )

    controller.delete_mesh(mesh_object)

    assert table_manager.get_data() == []
    assert scene.objects == []
    assert mesh_object.node not in mesh_root.children
