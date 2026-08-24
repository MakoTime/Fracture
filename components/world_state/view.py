from PySide6.QtCore import QDate, QDateTime, QTime, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from tools.widgets import MediaControlsWidget


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

    def __init__(self, parent=None, timer_controller=None):
        super().__init__(parent)
        self.timer_controller = timer_controller
        self.media_controls = MediaControlsWidget(self)
        self.rewind_button = self.media_controls.rewind_button
        self.play_pause_button = self.media_controls.play_pause_button
        self.fast_forward_button = self.media_controls.fast_forward_button

        self.time_spinbox = QTimeEdit(QTime.currentTime())
        self.time_spinbox.setDisplayFormat("HH:mm:ss")
        self.time_spinbox.setAccessibleName("World state time")
        self.date_spinbox = QDateEdit(QDate.currentDate())
        self.date_spinbox.setDisplayFormat("yyyy-MM-dd")
        self.date_spinbox.setCalendarPopup(True)
        self.date_spinbox.setAccessibleName("World state date")
        self._last_datetime = QDateTime(
            self.date_spinbox.date(), self.time_spinbox.time()
        )
        self.rate_combo = QComboBox()
        self.rate_combo.setAccessibleName("World state advancement unit")
        for label, unit in self.TIME_UNITS:
            self.rate_combo.addItem(label, unit)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.addWidget(QLabel("Time"))
        time_row.addWidget(self.time_spinbox)
        time_row.addStretch(1)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.addWidget(QLabel("Date"))
        date_row.addWidget(self.date_spinbox)
        date_row.addStretch(1)

        rate_row = QHBoxLayout()
        rate_row.setContentsMargins(0, 0, 0, 0)
        rate_row.addWidget(QLabel("Advance by"))
        rate_row.addWidget(self.rate_combo)
        rate_row.addStretch(1)

        timer_layout = QVBoxLayout()
        timer_layout.setContentsMargins(8, 8, 8, 8)
        timer_layout.addWidget(self.media_controls)
        timer_layout.addLayout(rate_row)
        timer_group = QGroupBox("Timer")
        timer_group.setLayout(timer_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(timer_group)
        layout.addLayout(time_row)
        layout.addLayout(date_row)

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
        self.date_spinbox.editingFinished.connect(self._datetime_edited)
        self.time_spinbox.editingFinished.connect(self._datetime_edited)

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
        fast_forward_rates = {1: 8, 2: 2, 3: 4}
        self._advance_amount = fast_forward_rates[self.fast_forward_button.speed()]
        self._reset_interpolation()
        self.advance_timer.start()

    def _reset_interpolation(self):
        self._interpolation_start = None
        self._interpolation_target = None
        self._interpolation_elapsed = 0

    def _datetime_edited(self):
        """Forward manual date/time edits to registered timer interfaces."""
        current = QDateTime(self.date_spinbox.date(), self.time_spinbox.time())
        delta_seconds = (
            current.toMSecsSinceEpoch() - self._last_datetime.toMSecsSinceEpoch()
        ) / 1000
        self._last_datetime = current
        self._reset_interpolation()
        if self.timer_controller is not None and delta_seconds:
            self.timer_controller.advance(delta_seconds)

    def _advance_time(self, elapsed_ms=None):
        if self._advance_amount == 0:
            return
        current = QDateTime(self.date_spinbox.date(), self.time_spinbox.time())
        if self._interpolation_target is None:
            self._interpolation_start = current
            self._interpolation_target = self._add_selected_time(current)
            self._interpolation_elapsed = 0

        previous_elapsed = self._interpolation_elapsed
        self._interpolation_elapsed += (
            self.advance_timer.interval() if elapsed_ms is None else elapsed_ms
        )
        progress = min(1.0, self._interpolation_elapsed / 1000)
        duration = self._interpolation_target.toMSecsSinceEpoch() - (
            self._interpolation_start.toMSecsSinceEpoch()
        )
        interpolated = self._interpolation_start.addMSecs(int(duration * progress))
        self.date_spinbox.setDate(interpolated.date())
        self.time_spinbox.setTime(interpolated.time())
        self._last_datetime = interpolated
        if self.timer_controller is not None:
            elapsed_delta = (
                (duration / 1000)
                * (self._interpolation_elapsed - previous_elapsed)
                / 1000
            )
            self.timer_controller.advance(elapsed_delta)
        if progress >= 1.0:
            self._reset_interpolation()

    def _add_selected_time(self, current):
        amount = self._advance_amount
        unit = self.rate_combo.currentData()
        if unit == "seconds":
            return current.addSecs(amount)
        if unit == "minutes":
            return current.addSecs(amount * 60)
        if unit == "hours":
            return current.addSecs(amount * 60 * 60)
        if unit == "days":
            return current.addDays(amount)
        if unit == "months":
            return current.addMonths(amount)
        return current.addYears(amount)
