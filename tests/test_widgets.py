from tools.widgets import VisibleWidget
from components.table import TableView
from dialog.mesh.model import MeshImportModel
from dialog.mesh.view import MeshImportView
from objects.object_base import ObjectBase


def test_visible_widget_starts_with_invisible_state(qapp):
    widget = VisibleWidget()

    assert widget.is_visible() is False
    assert widget.toolTip() == "Show object"
    assert not widget.icon().isNull()


def test_visible_widget_switches_icon_state_and_highlights(qapp):
    widget = VisibleWidget(visible=True)

    assert widget.is_visible() is True
    assert widget.toolTip() == "Hide object"
    assert not widget.icon().isNull()
    assert "QToolButton:hover" in widget.styleSheet()
    assert "QToolButton:checked" in widget.styleSheet()

    widget.set_visible(False)
    assert widget.is_visible() is False
    assert widget.toolTip() == "Show object"

    widget.click()
    assert widget.is_visible() is True


def test_table_view_uses_visible_widget_for_visible_column(qapp):
    table_view = TableView()
    object_base = ObjectBase("Table Visibility", visible=False)
    table_view.table_model.add_row(object_base.row_data)

    index = table_view.table_model.index(0, table_view.table_model.VISIBLE)
    widget = table_view.indexWidget(index)

    assert isinstance(widget, VisibleWidget)
    assert widget.is_visible() is False

    widget.click()

    assert object_base.visible is True


def test_mesh_import_destination_checkbox_updates_model(qapp):
    model = MeshImportModel()
    view = MeshImportView(model)

    assert model.add_to_scene is False
    assert view.add_to_scene.isChecked() is False

    view.add_to_scene.setChecked(True)
    view.update_model()

    assert model.add_to_scene is True
