from PySide6.QtCore import (
    QEvent,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QKeyEvent

from src.common.calendar.model import DateModel
from src.common.calendar.time import WorldTime, WorldTimeDelta
from src.common.icons import BIN_ICON, CLOCK_DOWNLOAD_ICON, CLOCK_UPLOAD_ICON
from src.components.world_state.model import WorldStateModel
from src.tools.widgets.world_calendar import QWorldDateEdit, QWorldTimeEdit
from .model import SavedTimesTableModel
from src.engine.block_objects.world_config import SavedTimes
from src.tools.widgets import MediaControlsWidget


class GoToDelegate(QStyledItemDelegate):
    """Draw and handle saved-time actions in the table."""

    clicked = Signal(int, str)
    ACTIONS = (
        ("load", CLOCK_UPLOAD_ICON),
        ("save", CLOCK_DOWNLOAD_ICON),
        ("remove", BIN_ICON),
    )

    @classmethod
    def actions_for_row(cls, row, saved_row_count):
        if row >= saved_row_count:
            return (cls.ACTIONS[1],)
        return cls.ACTIONS

    def paint(self, painter, option, index):
        if index.column() != SavedTimesTableModel.ACTIVATE:
            super().paint(painter, option, index)
            return

        actions = self.actions_for_row(
            index.row(),
            index.model().saved_time_count,
        )
        for action_index, (_, icon) in enumerate(actions):
            button = QStyleOptionButton()
            button.rect = self._button_rect(
                option.rect,
                action_index,
                len(actions),
            )
            button.icon = icon
            button.iconSize = QSize(18, 18)
            if option.state & QStyle.StateFlag.State_MouseOver:
                button.state |= QStyle.StateFlag.State_MouseOver
            if option.state & QStyle.StateFlag.State_Selected:
                button.state |= QStyle.StateFlag.State_HasFocus
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_PushButton,
                button,
                painter,
            )

    def editorEvent(self, event, model, option, index):
        if index.column() != SavedTimesTableModel.ACTIVATE:
            return super().editorEvent(event, model, option, index)

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                actions = self.actions_for_row(
                    index.row(),
                    model.saved_time_count,
                )
                for action_index, (action, _) in enumerate(actions):
                    button_rect = self._button_rect(
                        option.rect,
                        action_index,
                        len(actions),
                    )
                    if button_rect.contains(event.position().toPoint()):
                        self.clicked.emit(index.row(), action)
                        return True

        return False

    @staticmethod
    def _button_rect(rect: QRect, index: int, action_count: int):
        """Return one of the action button rectangles inside the cell."""
        width = 28
        height = 28
        total_width = width * action_count
        start_x = rect.x() + (rect.width() - total_width) // 2
        x = start_x + index * width
        y = rect.y() + (rect.height() - height) // 2

        return QRect(x, y, width, height)


class SavedTimesTableView(QTableView):
    """Table view for the saved times in the world configuration."""

    DATE_WIDTH = 162
    TIME_WIDTH = 57
    ACTION_WIDTH = 96
    NAME_MINIMUM_WIDTH = 120
    MINIMUM_WIDTH = DATE_WIDTH + TIME_WIDTH + ACTION_WIDTH + NAME_MINIMUM_WIDTH

    time_set = Signal(WorldTime)
    action_requested = Signal(int, str)

    def __init__(self, model: WorldStateModel, parent=None):
        super().__init__(parent)

        self.world_state_model = model
        self.table_model = SavedTimesTableModel(
            model,
            parent=self,
        )
        self.setModel(self.table_model)

        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # "Go to" button delegate
        self.go_to_delegate = GoToDelegate(self)
        self.go_to_delegate.clicked.connect(self.handle_time_set)

        self.setItemDelegateForColumn(
            SavedTimesTableModel.ACTIVATE,
            self.go_to_delegate,
        )
        self.table_model.rowsInserted.connect(self._refresh_date_widgets)
        self.table_model.rowsRemoved.connect(self._refresh_date_widgets)
        self.table_model.modelReset.connect(self._refresh_date_widgets)
        self.table_model.dataChanged.connect(self._refresh_date_widgets)

        header = self.horizontalHeader()
        header.setSectionResizeMode(
            SavedTimesTableModel.HEADER,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            SavedTimesTableModel.DATE,
            QHeaderView.ResizeMode.Fixed,
        )
        header.resizeSection(SavedTimesTableModel.DATE, self.DATE_WIDTH)
        header.setSectionResizeMode(
            SavedTimesTableModel.TIME,
            QHeaderView.ResizeMode.Fixed,
        )
        header.resizeSection(SavedTimesTableModel.TIME, self.TIME_WIDTH)
        header.setSectionResizeMode(
            SavedTimesTableModel.ACTIVATE,
            QHeaderView.ResizeMode.Fixed,
        )
        header.resizeSection(SavedTimesTableModel.ACTIVATE, self.ACTION_WIDTH)
        self.verticalHeader().setVisible(False)
        self.setMinimumWidth(self.MINIMUM_WIDTH)
        self._refresh_date_widgets()

    def _refresh_date_widgets(self, *args):
        for row_index in range(self.table_model.saved_time_count):
            saved_time = self.table_model.saved_time_at(row_index)
            index = self.table_model.index(row_index, SavedTimesTableModel.DATE)
            widget = self.indexWidget(index)
            if not isinstance(widget, QWorldDateEdit):
                widget = QWorldDateEdit(saved_time.date, self)
                widget.setDisplayFormat("dd MMMM yyyy")
                widget.setCalendarPopup(True)
                widget.dateChanged.connect(
                    lambda date, editor=widget: self._date_widget_changed(
                        editor,
                        date,
                    )
                )
                self.setIndexWidget(index, widget)
            else:
                widget.setDate(
                    DateModel(
                        year=saved_time.date.year,
                        month=saved_time.date.month,
                        day=saved_time.date.day,
                    )
                )

    def _date_widget_changed(self, widget, date):
        for row_index in range(self.table_model.saved_time_count):
            index = self.table_model.index(row_index, SavedTimesTableModel.DATE)
            if self.indexWidget(index) is widget:
                current = self.table_model.saved_time_at(row_index).date
                self.table_model.setData(
                    index,
                    WorldTime(
                        year=date.year,
                        month=date.month,
                        day=date.day,
                        hours=current.hours,
                        minutes=current.minutes,
                        seconds=current.seconds,
                        milliseconds=current.milliseconds,
                    ),
                )
                return

    def index_at_row(self, row):
        return self.table_model.index(row, 0)

    def add_row(self, name, date_time):
        self.table_model.add_row(name, date_time)
        self.world_state_model.saved_times_updated()

    def remove_row(self, row):
        self.table_model.remove_row(row)
        self.world_state_model.saved_times_updated()

    def edit_row(self, row, name, date_time):
        self.table_model.edit_row(row, name, date_time)

    def update_row_time(self, row, date_time):
        self.table_model.update_row_time(row, date_time)
        self.world_state_model.saved_times_updated()

    def handle_time_set(self, row, action):
        """Handle an action for a saved timestamp or the blank row."""
        saved_row_count = self.table_model.saved_time_count
        if row >= saved_row_count:
            if action == "save":
                self.action_requested.emit(row, action)
            return

        saved_time = self.table_model.saved_time_at(row)
        if action == "load":
            self.time_set.emit(saved_time.date)
        else:
            self.action_requested.emit(row, action)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (
            Qt.Key.Key_Delete,
            Qt.Key.Key_Backspace,
        ):
            selected_rows = self.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                if row < self.table_model.saved_time_count:
                    self.action_requested.emit(row, "remove")
                    event.accept()
                    return
        super().keyPressEvent(event)


class WorldStateView(QWidget):
    """Compact read-only view of the active project's state."""

    TIME_UNITS = (
        ("Seconds", "seconds"),
        ("Minutes", "minutes"),
        ("Hours", "hours"),
        ("Days", "days"),
        ("Months", "months"),
        ("Years", "years"),
    )

    def __init__(
        self, parent=None, timer_controller=None, model: WorldStateModel = None
    ):
        super().__init__(parent)
        self.model = model if model is not None else WorldStateModel()
        self.timer_controller = timer_controller

        self.media_controls = MediaControlsWidget(self)
        self.rewind_button = self.media_controls.rewind_button
        self.play_pause_button = self.media_controls.play_pause_button
        self.fast_forward_button = self.media_controls.fast_forward_button

        self.time_spinbox = QWorldTimeEdit(
            self.model.date_time
        )
        self.time_spinbox.setDisplayFormat("HH:mm:ss")
        self.time_spinbox.setAccessibleName("World state time")

        self.date_spinbox = QWorldDateEdit(
            self.model.date_time
        )
        self.date_spinbox.setDisplayFormat("dd/MM/yyyy")
        self.date_spinbox.setCalendarPopup(True)
        self.date_spinbox.setAccessibleName("World state date")

        self._last_time = self.model.date_time

        self.rate_combo = QComboBox()
        self.rate_combo.setAccessibleName("World state advancement unit")

        for label, unit in self.TIME_UNITS:
            self.rate_combo.addItem(label, unit)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(8)
        time_row.addWidget(QLabel("Time"))
        time_row.addWidget(self.time_spinbox)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(8)
        date_row.addWidget(QLabel("Date"))
        date_row.addWidget(self.date_spinbox)

        rate_row = QHBoxLayout()
        rate_row.setContentsMargins(0, 0, 0, 0)
        rate_row.setSpacing(8)
        rate_row.addWidget(QLabel("Advance by"))
        rate_row.addWidget(self.rate_combo)

        timer_layout = QVBoxLayout()
        timer_layout.setContentsMargins(12, 12, 12, 12)
        timer_layout.setSpacing(8)

        media_row = QHBoxLayout()
        media_row.setContentsMargins(0, 0, 0, 0)
        media_row.addStretch(1)
        media_row.addWidget(self.media_controls)
        media_row.addStretch(1)

        timer_layout.addLayout(media_row)
        timer_layout.addSpacing(8)
        timer_layout.addLayout(rate_row)
        timer_layout.addLayout(time_row)
        timer_layout.addLayout(date_row)

        timer_group = QGroupBox("Timer")
        timer_group.setLayout(timer_layout)
        timer_group.setMinimumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(timer_group)

        self.advance_timer = QTimer(self)
        self.advance_timer.setInterval(16)
        self.advance_timer.timeout.connect(self._advance_time)

        self._advance_amount = 0
        self._interpolation_start = None
        self._interpolation_target = None
        self._interpolation_elapsed = 0

        self.rewind_button.clicked.connect(self._start_rewind)
        self.play_pause_button.clicked.connect(self._toggle_playback)
        self.fast_forward_button.clicked.connect(self._start_fast_forward)

        self.date_spinbox.dateChanged.connect(self._datetime_edited)
        self.time_spinbox.timeChanged.connect(self._datetime_edited)
        self.model.world_state_changed.connect(self._model_changed)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.datetime_table = SavedTimesTableView(self.model, self)
        self._connect_datetime_table()
        layout.addWidget(self.datetime_table)
        self.setMinimumWidth(self.datetime_table.minimumWidth())

    def initialize_model(self, model: WorldStateModel):
        try:
            self.model.world_state_changed.disconnect(self._model_changed)
        except RuntimeError:
            pass

        self.model = model

        self.model.world_state_changed.connect(self._model_changed)

        self._model_changed()

        self.datetime_table.setParent(None)
        self.datetime_table.deleteLater()
        self.datetime_table = SavedTimesTableView(
            self.model,
            self,
        )
        self._connect_datetime_table()
        self.layout().addWidget(self.datetime_table)

    def _connect_datetime_table(self):
        self.datetime_table.time_set.connect(self._set_saved_time)
        self.datetime_table.action_requested.connect(
            self._handle_saved_time_action
        )

    def _set_saved_time(self, value: WorldTime):
        if self.timer_controller is not None:
            self.timer_controller.set_time(value)
        self.model.date_time = value

    def _handle_saved_time_action(self, row: int, action: str):
        saved_row_count = self.model.saved_time_count
        if row >= saved_row_count:
            if action != "save":
                return
            self.datetime_table.add_row("", self.model.date_time)
        elif action == "save":
            self.datetime_table.update_row_time(row, self.model.date_time)
        elif action == "remove":
            self.datetime_table.remove_row(row)
        else:
            return

    def _model_changed(self):
        if self.model is None:
            return

        value = self.model.date_time

        self.date_spinbox.blockSignals(True)
        self.time_spinbox.blockSignals(True)

        self.date_spinbox.setDate(DateModel(year=value.year, month=value.month, day=value.day))
        self.time_spinbox.setTime(value)

        self.date_spinbox.blockSignals(False)
        self.time_spinbox.blockSignals(False)

        self._last_time = value

    def set_scene_model(self, scene_model):
        del scene_model

    def refresh(self):
        return None

    def _toggle_playback(self):
        if self.play_pause_button.is_playing():
            self._advance_amount = 1
            self._reset_interpolation()
            self.advance_timer.start()
        else:
            self._advance_amount = 0
            self._reset_interpolation()
            self.advance_timer.stop()

    def _start_rewind(self):
        self._advance_amount = -(2 ** (self.rewind_button.speed() - 1))
        self._reset_interpolation()
        self.advance_timer.start()

    def _start_fast_forward(self):
        fast_forward_rates = {1: 2, 2: 4, 3: 8}
        self._advance_amount = fast_forward_rates[self.fast_forward_button.speed()]
        self._reset_interpolation()
        self.advance_timer.start()

    def _reset_interpolation(self):
        self._interpolation_start = None
        self._interpolation_target = None
        self._interpolation_elapsed = 0

    def _datetime_edited(self):
        if self.sender() is self.time_spinbox:
            current = self.time_spinbox.time()
        else:
            current = WorldTime.join_date_time(
                self.date_spinbox.date(),
                self.time_spinbox.time(),
            )

        delta_seconds = (current - self._last_time).total_seconds()
        self.model.date_time = current
        self._reset_interpolation()

        if self.timer_controller is not None and delta_seconds:
            self.timer_controller.advance(delta_seconds)

    def _advance_time(self, elapsed_ms=None):
        if self._advance_amount == 0:
            return
        current = self.model.date_time
        if self._interpolation_target is None:
            self._interpolation_start = current
            self._interpolation_delta = self._selected_time_delta()
            self._interpolation_target = current.advance(
                self._interpolation_delta,
            )
            self._interpolation_duration = (
                self._interpolation_target - self._interpolation_start
            ).total_seconds()
            self._interpolation_elapsed = 0
        previous_elapsed = self._interpolation_elapsed
        self._interpolation_elapsed += (
            self.advance_timer.interval()
            if elapsed_ms is None
            else elapsed_ms
        )
        progress = min(1.0, self._interpolation_elapsed / 1000)
        interpolation_seconds = self._interpolation_duration * progress
        interpolated = self._interpolation_start.advance(
            WorldTimeDelta(milliseconds=interpolation_seconds * 1000),
        )
        self.model.date_time = interpolated
        if self.timer_controller is not None:
            elapsed_delta = (
                self._interpolation_duration
                * (self._interpolation_elapsed - previous_elapsed)
                / 1000
            )
            self.timer_controller.advance(elapsed_delta)
        if progress >= 1.0:
            self._reset_interpolation()

    def _selected_time_delta(self) -> WorldTimeDelta:
        amount = self._advance_amount
        unit = self.rate_combo.currentData()
        if unit == "seconds":
            return WorldTimeDelta(seconds=amount)
        if unit == "minutes":
            return WorldTimeDelta(minutes=amount)
        if unit == "hours":
            return WorldTimeDelta(hours=amount)
        if unit == "days":
            return WorldTimeDelta(days=amount)
        if unit == "months":
            return WorldTimeDelta(months=amount)
        if unit == "years":
            return WorldTimeDelta(years=amount)
        raise ValueError(f"Unknown advance unit: {unit!r}")
