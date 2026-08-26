from datetime import datetime, timezone

from src.common.calendar import (
    Calendar,
    CalendarEpoch,
    DateModel,
    DayLength,
    Era,
    Month,
    WorldTime,
)
from src.components.table import TableManager, TableView
from src.components.world_state import WorldStateView
from src.components.world_state.model import WorldStateModel
from src.dialog.mesh_import.model import MeshImportModel
from src.dialog.mesh_import.view import MeshImportView
from src.objects.mesh_object import MeshObject
from src.tests.viewable_test_object import ViewableTestObject
from src.tools.widgets import (
    DynamicSpinbox,
    FastForwardWidget,
    MediaControlsWidget,
    NormalizedSpinBox,
    PlayPauseWidget,
    RewindWidget,
    VisibleWidget,
)
from src.tools.widgets.world_calendar import (
    QWorldCalendarPopup,
    QWorldDateEdit,
    QWorldTimeEdit,
)


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
    assert view.date_spinbox.displayFormat() == "dd/MM/yyyy"
    assert [
        view.rate_combo.itemData(index) for index in range(view.rate_combo.count())
    ] == [
        "seconds",
        "minutes",
        "hours",
        "days",
        "months",
        "years",
    ]

    assert view.layout().indexOf(view.datetime_table) >= 0


def test_saved_time_actions_mutate_rows_through_world_state_model(qapp):
    view = WorldStateView()
    first_time = WorldTime(2026, 0, 1, 1, 2, 3)
    second_time = WorldTime(2026, 0, 2, 4, 5, 6)

    view.model.date_time = first_time
    view._handle_saved_time_action(0, "save")
    assert view.model.saved_time_count == 1
    assert view.model.saved_time_at(0).date == first_time

    view.model.date_time = second_time
    view._handle_saved_time_action(0, "save")
    assert view.model.saved_time_count == 1
    assert view.model.saved_time_at(0).date == second_time

    view._handle_saved_time_action(0, "remove")
    assert view.model.saved_time_count == 0
    assert view.datetime_table.table_model.rowCount() == 1


def test_saved_times_table_refreshes_after_world_state_load(qapp):
    view = WorldStateView()
    view.initialize_model(WorldStateModel.from_object(view.model.world_state_object))
    loaded_time = WorldTime(2026, 2, 4, 7, 8, 9)
    loaded_data = {
        "name": "World State",
        "date_time": loaded_time.to_dict(),
        "saved_times": {
            "rows": [{"name": "Imported time", "date": loaded_time.to_dict()}]
        },
    }

    view.model.world_state_object.deserialise_to_block(loaded_data)

    assert view.model.saved_time_count == 1
    assert view.datetime_table.table_model.rowCount() == 2
    assert view.datetime_table.table_model.data(
        view.datetime_table.table_model.index(0, 0)
    ) == "Imported time"


def test_calendar_popup_offsets_month_start_from_epoch_weekday(qapp):
    calendar = Calendar(
        day_length=DayLength(24, 0, 0),
        weekdays=("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
        seasons=(),
        months=(Month("first", "First", 30), Month("second", "Second", 31)),
        eras={},
        epoch=CalendarEpoch(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            year=0,
            month=0,
            day=0,
        ),
    )
    popup = QWorldCalendarPopup(calendar, DateModel(0, 1, 0))

    assert popup._grid.itemAtPosition(1, 2).widget().text() == "1"


def test_calendar_popup_uses_fixed_size_cells(qapp):
    calendar = Calendar(
        day_length=DayLength(24, 0, 0),
        weekdays=("Mon", "Tue"),
        seasons=(),
        months=(Month("first", "First", 30),),
        eras={"BCE": Era(None, -1)},
        epoch=CalendarEpoch(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            year=0,
            month=0,
            day=0,
        ),
    )
    popup = QWorldCalendarPopup(calendar, DateModel(0, 0, 0))

    assert popup._grid.itemAtPosition(0, 0).widget().size() == popup._CELL_SIZE
    assert popup._grid.itemAtPosition(1, 0).widget().size() == popup._CELL_SIZE


def test_calendar_popup_displays_signed_year_and_short_weekdays(qapp):
    calendar = Calendar(
        day_length=DayLength(24, 0, 0),
        weekdays=("Monday", "Tuesday"),
        seasons=(),
        months=(Month("first", "First", 30),),
        eras={"BCE": Era(None, -1)},
        epoch=CalendarEpoch(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            year=0,
            month=0,
            day=0,
        ),
    )
    popup = QWorldCalendarPopup(calendar, DateModel(-500, 0, 0))

    assert popup._year.text() == "-500"
    assert popup._grid.itemAtPosition(0, 0).widget().text() == "Mo"
    assert popup._grid.itemAtPosition(0, 1).widget().text() == "Tu"


def test_calendar_popup_grows_for_months_with_more_week_rows(qapp):
    calendar = Calendar(
        day_length=DayLength(24, 0, 0),
        weekdays=("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
        seasons=(),
        months=(Month("short", "Short", 28), Month("long", "Long", 35)),
        eras={"BCE": Era(None, -1)},
        epoch=CalendarEpoch(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            year=0,
            month=0,
            day=0,
        ),
    )
    popup = QWorldCalendarPopup(calendar, DateModel(0, 0, 0))
    short_height = popup.height()

    popup.setDate(DateModel(0, 1, 0))

    assert popup.height() > short_height


def test_world_state_media_controls_advance_selected_time(qapp):
    view = WorldStateView()
    view.model.date_time = WorldTime(2026, 0, 30, 23, 59, 59)

    view.rate_combo.setCurrentIndex(0)
    view.play_pause_button.click()
    view._advance_time(1000)
    assert view.date_spinbox.date() == DateModel(2026, 1, 0)
    assert view.time_spinbox.time() == WorldTime(2026, 1, 0, 0, 0, 0)

    view.fast_forward_button.click()
    view._advance_time(1000)
    assert view.time_spinbox.time().seconds == 4

    view.fast_forward_button.click()
    view._advance_time(1000)
    assert view.time_spinbox.time().seconds == 12

    view.fast_forward_button.click()
    view._advance_time(1000)
    assert view.time_spinbox.time().seconds == 14

    view.rate_combo.setCurrentIndex(4)
    view._advance_time(1000)
    assert view.date_spinbox.date() == DateModel(2026, 3, 0)


def test_world_date_edit_commits_valid_text_on_editing_finished(qapp):
    widget = QWorldDateEdit(WorldTime(2026, 0, 0, 0, 0, 0))
    widget.setDisplayFormat("dd/MM/yyyy")
    widget._editor.setText("02/03/2026")

    widget._editor.editingFinished.emit()

    assert widget.date() == DateModel(2026, 2, 1)


def test_world_date_edit_reverts_invalid_text_on_editing_finished(qapp):
    widget = QWorldDateEdit(WorldTime(2026, 0, 0, 0, 0, 0))
    widget.setDisplayFormat("dd/MM/yyyy")
    widget._editor.setText("32/03/2026")

    widget._editor.editingFinished.emit()

    assert widget.date() == DateModel(2026, 0, 0)
    assert widget._editor.text() == "01/01/2026"


def test_world_date_edit_shows_the_current_era(qapp):
    calendar = Calendar(
        day_length=DayLength(24, 0, 0),
        weekdays=("Mon",),
        seasons=(),
        months=(Month("jan", "January", 31),),
        eras={"BCE": Era(None, -1), "Current": Era(0, None)},
        epoch=CalendarEpoch(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    widget = QWorldDateEdit()
    widget.setCalendar(calendar)
    widget.setDate(DateModel(-1, 0, 0))

    assert widget._era_label.text() == "BCE"

    widget.setDate(DateModel(0, 0, 0))

    assert widget._era_label.text() == "Current"


def test_world_date_edit_displays_negative_years_as_absolute_values(qapp):
    widget = QWorldDateEdit()
    widget.setDisplayFormat("yyyy/MM/dd")
    widget.setCalendar(
        Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Mon",),
            seasons=(),
            months=(Month("jan", "January", 31),),
            eras={"BCE": Era(None, -1)},
            epoch=CalendarEpoch(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )
    )
    widget.setDate(DateModel(-500, 0, 0))

    assert widget._editor.text() == "0500/01/01"


def test_world_state_datetime_edits_advance_timer_interfaces(qapp):
    class TimerController:
        def __init__(self):
            self.deltas = []

        def advance(self, delta_seconds):
            self.deltas.append(delta_seconds)

    timer_controller = TimerController()
    view = WorldStateView(timer_controller=timer_controller)
    view.model.date_time = WorldTime(2026, 0, 0, 0, 0, 0)

    view.time_spinbox.setTime(WorldTime(2026, 0, 0, 0, 0, 5))
    view._datetime_edited()

    assert timer_controller.deltas == [5.0]


def test_world_state_time_advancement_interpolates(qapp):
    view = WorldStateView()
    view.model.date_time = WorldTime(2026, 0, 0, 0, 0, 0)

    view.play_pause_button.click()
    view._advance_time(500)

    assert view.time_spinbox.time().seconds == 0
    assert view.time_spinbox.time().milliseconds == 500

    view._advance_time(500)
    assert view.time_spinbox.time().seconds == 1


def test_world_state_time_spinbox_rollover_updates_date(qapp):
    view = WorldStateView()
    view.model.date_time = WorldTime(2026, 0, 0, 23, 59, 59)

    view.time_spinbox._hour.spinbox.stepUp()

    assert view.model.date_time == WorldTime(2026, 0, 1, 0, 59, 59)
    assert view.date_spinbox.date() == DateModel(2026, 0, 1)


def test_world_time_edit_wraps_seconds_into_minutes(qapp):
    widget = QWorldTimeEdit()
    widget.setTime(WorldTime(2026, 0, 0, 0, 0, 59))

    widget._second.spinbox.stepUp()

    assert widget.time() == WorldTime(2026, 0, 0, 0, 1, 0)


def test_world_time_edit_wraps_hours_into_custom_calendar_day(qapp):
    widget = QWorldTimeEdit()
    widget.setTime(WorldTime(2026, 0, 0, 23, 59, 59))

    widget._hour.spinbox.stepUp()

    assert widget.time() == WorldTime(2026, 0, 1, 0, 59, 59)


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
    object_base = ViewableTestObject("Table Visibility", visible=False)
    table_view.table_model.add_row(object_base.row_data)

    index = table_view.table_model.index(0, table_view.table_model.VISIBLE)
    widget = table_view.indexWidget(index)

    assert isinstance(widget, VisibleWidget)
    assert widget.is_visible() is False

    widget.click()

    assert object_base.visible is True


def test_table_model_refresh_object_notifies_registered_row(qapp):
    table_view = TableView()
    object_base = ViewableTestObject("Refreshable")
    table_view.table_model.add_row(object_base.row_data)
    changed = []
    table_view.table_model.dataChanged.connect(
        lambda top_left, bottom_right: changed.append(
            (top_left.row(), bottom_right.column())
        )
    )

    assert table_view.table_model.refresh_object(object_base) is True
    assert changed == [(0, table_view.table_model.columnCount() - 1)]


def test_object_block_change_refreshes_table_and_scene_views(qapp):
    class FakeScene:
        def __init__(self):
            self.refreshed = []

        def add_object(self, object_base):
            return object_base

        def refresh_object(self, object_base):
            self.refreshed.append(object_base)

    mesh = MeshObject("Refreshable mesh")
    table_manager = TableManager()
    table_model = TableView(table_manager=table_manager).table_model
    scene = FakeScene()
    mesh.add_to_table(table_manager)
    mesh.add_to_scene(scene)

    mesh.mesh_block_object.mark_changed()

    assert scene.refreshed == [mesh]
    assert table_model.rowCount() == 1


def test_mesh_import_destination_checkbox_updates_model(qapp):
    model = MeshImportModel()
    view = MeshImportView(model, deduper=lambda name: name)

    assert model.add_to_scene is False
    assert view.add_to_scene.isChecked() is False

    view.add_to_scene.setChecked(True)
    view.update_model()

    assert model.add_to_scene is True
