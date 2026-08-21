from PySide6.QtCore import QDate, QTime

from tools.widgets import (
    FastForwardWidget,
    MediaControlsWidget,
    PlayPauseWidget,
    RewindWidget,
    VisibleWidget,
)
from components.table import TableView
from dialog.mesh_import.model import MeshImportModel
from dialog.mesh_import.view import MeshImportView
from components.world_state import WorldStateView
from dialog.mesh_generate.view import NormalizedSpinBox
from tools.widgets import DynamicSpinbox
from objects.object_base import ObjectBase


def test_visible_widget_starts_with_invisible_state(qapp):
    widget = VisibleWidget()

    assert widget.is_visible() is False
    assert widget.toolTip() == "Show object"
    assert not widget.icon().isNull()


def test_normalized_spinbox_uses_a_fine_unit_interval_step(qapp):
    widget = NormalizedSpinBox()

    assert widget.minimum() == 0.0
    assert widget.maximum() == 1.0
    assert widget.decimals() == 3
    assert widget.singleStep() == 0.01


def test_dynamic_spinbox_uses_tenth_of_range_with_base_ten_steps(qapp):
    widget = DynamicSpinbox()
    widget.setRange(0.0, 1.0)
    assert widget.singleStep() == 0.1

    widget.setRange(90.0, 91.0)
    assert widget.singleStep() == 0.1

    widget.setRange(0.0, 100.0)
    assert widget.singleStep() == 10.0


def test_play_pause_widget_switches_icon_and_tooltip(qapp):
    widget = PlayPauseWidget()

    assert widget.is_playing() is False
    assert widget.toolTip() == "Play"
    assert not widget.icon().isNull()

    widget.click()
    assert widget.is_playing() is True
    assert widget.toolTip() == "Pause"

    widget.set_playing(False)
    assert widget.toolTip() == "Play"


def test_world_state_view_has_transport_controls_in_order(qapp):
    view = WorldStateView()

    assert view.rewind_button.toolTip() == "Rewind (1x)"
    assert view.play_pause_button.toolTip() == "Play"
    assert view.fast_forward_button.toolTip() == "Fast forward (1x)"
    assert not view.rewind_button.icon().isNull()
    assert not view.fast_forward_button.icon().isNull()


def test_stepped_transport_widgets_cycle_to_three_speeds(qapp):
    rewind = RewindWidget()
    fast_forward = FastForwardWidget()

    rewind.click()
    fast_forward.click()
    assert rewind.speed() == 2
    assert fast_forward.speed() == 2
    assert rewind.toolTip() == "Rewind (2x)"

    rewind.click()
    fast_forward.click()
    assert rewind.speed() == 3
    assert fast_forward.speed() == 3

    rewind.click()
    fast_forward.click()
    assert rewind.speed() == 1
    assert fast_forward.speed() == 1


def test_media_controls_reset_other_widgets_on_interaction(qapp):
    controls = MediaControlsWidget()

    controls.rewind_button.click()
    assert controls.rewind_button.speed() == 2
    assert controls.play_pause_button.is_playing() is False
    assert controls.fast_forward_button.speed() == 1

    controls.play_pause_button.click()
    assert controls.play_pause_button.is_playing() is True
    assert controls.rewind_button.speed() == 1
    assert controls.fast_forward_button.speed() == 1

    controls.fast_forward_button.click()
    assert controls.fast_forward_button.speed() == 2
    assert controls.rewind_button.speed() == 1
    assert controls.play_pause_button.is_playing() is False

    controls.play_pause_button.click()
    assert controls.play_pause_button.is_playing() is True
    assert controls.rewind_button.speed() == 1
    assert controls.fast_forward_button.speed() == 1


def test_world_state_view_has_time_above_date(qapp):
    view = WorldStateView()

    assert view.time_spinbox.displayFormat() == "HH:mm:ss"
    assert view.date_spinbox.displayFormat() == "yyyy-MM-dd"
    assert [view.rate_combo.itemData(index) for index in range(view.rate_combo.count())] == [
        "seconds",
        "minutes",
        "hours",
        "days",
        "months",
        "years",
    ]


def test_world_state_media_controls_advance_selected_time(qapp):
    view = WorldStateView()
    view.date_spinbox.setDate(QDate(2026, 1, 31))
    view.time_spinbox.setTime(QTime(23, 59, 59))

    view.rate_combo.setCurrentIndex(0)
    view.play_pause_button.click()
    view._advance_time(1000)
    assert view.date_spinbox.date() == QDate(2026, 2, 1)
    assert view.time_spinbox.time() == QTime(0, 0, 0)

    view.fast_forward_button.click()
    view._advance_time(1000)
    assert view.time_spinbox.time() == QTime(0, 0, 2)

    view.fast_forward_button.click()
    view._advance_time(1000)
    assert view.time_spinbox.time() == QTime(0, 0, 6)

    view.fast_forward_button.click()
    view._advance_time(1000)
    assert view.time_spinbox.time() == QTime(0, 0, 14)

    view.rate_combo.setCurrentIndex(4)
    view._advance_time(1000)
    assert view.date_spinbox.date() == QDate(2026, 10, 1)


def test_world_state_time_advancement_interpolates(qapp):
    view = WorldStateView()
    view.date_spinbox.setDate(QDate(2026, 1, 1))
    view.time_spinbox.setTime(QTime(0, 0, 0))

    view.play_pause_button.click()
    view._advance_time(500)

    assert view.time_spinbox.time() == QTime(0, 0, 0, 500)

    view._advance_time(500)
    assert view.time_spinbox.time() == QTime(0, 0, 1, 0)


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
