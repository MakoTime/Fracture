from types import SimpleNamespace

from PySide6.QtCore import Qt

from components.table import TableManager, TableModel
from components.tree import TreeModel
from components.tree.roots import mesh_root, root_objects
from dialog.mesh.model import MeshImportModel
from objects.mesh_object import MeshObject
from application.importers import MeshImportController, ObjectImporterModel
from objects.object_base import ObjectBase


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
