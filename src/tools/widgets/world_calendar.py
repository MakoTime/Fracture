from __future__ import annotations

import re

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.common.calendar import Calendar, DateModel, WorldTime, WorldTimeDelta
from src.common.calendar.time import WorldClock
from src.tools.widgets.spin_boxes import CompactSpinBox


class QWorldCalendarPopup(QDialog):
    dateSelected = Signal(DateModel)
    _CELL_SIZE = QSize(40, 28)

    def __init__(
        self,
        calendar: Calendar,
        date: DateModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.Popup)
        self._calendar = calendar
        self._date = date
        self._updating = False
        self._previous = QToolButton()
        self._previous.setText("◀")
        self._next = QToolButton()
        self._next.setText("▶")
        self._month = QComboBox()
        self._year = QSpinBox()
        self._year.setRange(-999_999, 999_999)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._previous)
        header.addWidget(self._month)
        header.addWidget(self._year)
        header.addWidget(self._next)
        self._grid = QGridLayout()
        self._grid.setSpacing(2)
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.addLayout(header)
        layout.addLayout(self._grid)
        self._populate_months()
        self._previous.clicked.connect(self._previous_month)
        self._next.clicked.connect(self._next_month)
        self._month.currentIndexChanged.connect(self._refresh)
        self._year.valueChanged.connect(self._refresh)
        self.setDate(date)

    def date(self) -> DateModel:
        return self._date

    def setDate(self, date: DateModel) -> None:
        self._date = date
        self._updating = True
        try:
            self._month.setCurrentIndex(date.month)
            self._year.setValue(date.year)
        finally:
            self._updating = False
        self._refresh()

    def _populate_months(self) -> None:
        self._month.clear()
        for month in self._calendar.months:
            self._month.addItem(month.name)

    def _previous_month(self) -> None:
        month = self._month.currentIndex()
        year = self._year.value()
        if month <= 0:
            month = self._calendar.month_count - 1
            year -= 1
        else:
            month -= 1
        self._updating = True
        try:
            self._month.setCurrentIndex(month)
            self._year.setValue(year)
        finally:
            self._updating = False
        self._refresh()

    def _next_month(self) -> None:
        month = self._month.currentIndex()
        year = self._year.value()
        if month >= self._calendar.month_count - 1:
            month = 0
            year += 1
        else:
            month += 1
        self._updating = True
        try:
            self._month.setCurrentIndex(month)
            self._year.setValue(year)
        finally:
            self._updating = False
        self._refresh()

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh(self) -> None:
        if self._updating:
            return
        self._clear_grid()
        weekday_count = max(len(self._calendar.weekdays), 1)
        for column, weekday in enumerate(self._calendar.weekdays):
            header = QPushButton(weekday[:2])
            header.setEnabled(False)
            header.setFixedSize(self._CELL_SIZE)
            self._grid.addWidget(header, 0, column)
        month = self._month.currentIndex()
        year = self._year.value()
        days = self._calendar.month_days(month, year)
        if days is None:
            return
        first_day_column = self._weekday_offset(year, month, 0, weekday_count)
        for day in range(days):
            weekday_offset = first_day_column + day
            row = weekday_offset // weekday_count + 1
            column = weekday_offset % weekday_count
            button = QPushButton(str(day + 1))
            button.setFixedSize(self._CELL_SIZE)
            button.setCheckable(True)
            button.setChecked(
                year == self._date.year
                and month == self._date.month
                and day == self._date.day
            )
            button.clicked.connect(
                lambda checked=False, value=day: self._select_day(value)
            )
            self._grid.addWidget(button, row, column)
        self.adjustSize()

    def _weekday_offset(
        self,
        year: int,
        month: int,
        day: int,
        weekday_count: int,
    ) -> int:
        epoch = self._calendar.epoch
        current_year = epoch.year
        current_month = epoch.month
        current_day = epoch.day
        offset = 0
        target = (year, month, day)
        current = (current_year, current_month, current_day)

        if target >= current:
            while current != target:
                offset += 1
                current_day += 1
                month_days = self._calendar.month_days(current_month, current_year)
                if month_days is None:
                    raise RuntimeError("Invalid calendar month.")
                if current_day >= month_days:
                    current_day = 0
                    current_month += 1
                    if current_month >= self._calendar.month_count:
                        current_month = 0
                        current_year += 1
                current = (current_year, current_month, current_day)
        else:
            while current != target:
                offset -= 1
                current_day -= 1
                if current_day < 0:
                    current_month -= 1
                    if current_month < 0:
                        current_month = self._calendar.month_count - 1
                        current_year -= 1
                    month_days = self._calendar.month_days(current_month, current_year)
                    if month_days is None:
                        raise RuntimeError("Invalid calendar month.")
                    current_day = month_days - 1
                current = (current_year, current_month, current_day)

        return offset % weekday_count

    def _select_day(self, day: int) -> None:
        self._date = DateModel(
            year=self._year.value(),
            month=self._month.currentIndex(),
            day=day,
        )
        self.dateSelected.emit(self._date)
        self.close()


class QWorldDateEdit(QWidget):
    dateChanged = Signal(DateModel)

    def __init__(
        self,
        world_time: WorldTime | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if world_time is not None:
            self._date = DateModel(
                year=world_time.year,
                month=world_time.month,
                day=world_time.day,
            )
            self._calendar = world_time.calendar
        else:
            self._date = DateModel(year=0, month=0, day=0)
            self._calendar = WorldClock.calendar()
        self._display_format = "yyyy/MM/dd"
        self._calendar_popup_enabled = False
        self._editor = QLineEdit()
        self._editor.editingFinished.connect(self._commit_edit)
        self._era_label = QLabel()
        self._calendar_button = QToolButton()
        self._calendar_button.setText("▼")
        self._calendar_button.setAutoRaise(True)
        self._calendar_button.setVisible(False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor)
        layout.addWidget(self._era_label)
        layout.addWidget(self._calendar_button)
        self._calendar_button.clicked.connect(self._show_calendar)
        self._update_text()

    def calendar(self) -> Calendar | None:
        return self._calendar

    def setCalendar(self, calendar: Calendar | None) -> None:
        self._calendar = calendar
        self._update_text()

    def date(self) -> DateModel:
        return self._date

    def setDate(self, date: DateModel) -> None:
        if self._calendar is not None:
            days = self._calendar.month_days(date.month, date.year)
            if days is None:
                raise ValueError(f"Invalid month: {date.month}")
            if not 0 <= date.day < days:
                raise ValueError(f"Invalid day: {date.day}")
        if date == self._date:
            return
        self._date = date
        self._update_text()
        self.dateChanged.emit(date)

    def setDisplayFormat(self, format: str) -> None:
        self._display_format = format
        self._update_text()

    def displayFormat(self) -> str:
        return self._display_format

    def setCalendarPopup(self, enabled: bool) -> None:
        self._calendar_popup_enabled = enabled
        self._calendar_button.setVisible(enabled)

    def calendarPopup(self) -> bool:
        return self._calendar_popup_enabled

    def _update_text(self) -> None:
        if self._calendar is None:
            self._editor.clear()
            self._era_label.clear()
            return
        month = self._calendar.get_month(self._date.month)
        if month is None:
            self._editor.clear()
            self._era_label.clear()
            return
        display_year = abs(self._date.year)
        replacements = {
            "yyyy": f"{display_year:04d}",
            "yy": f"{display_year % 100:02d}",
            "MMMM": month.name,
            "MM": f"{self._date.month + 1:02d}",
            "M": str(self._date.month + 1),
            "dd": f"{self._date.day + 1:02d}",
            "d": str(self._date.day + 1),
        }
        text = re.sub(
            r"yyyy|yy|MMMM|MM|M|dd|d",
            lambda match: replacements[match.group()],
            self._display_format,
        )
        self._editor.setText(text)
        self._era_label.setText(self._calendar.era_for_year(self._date.year) or "")

    def _commit_edit(self) -> None:
        if self._calendar is None:
            self._update_text()
            return

        token_pattern = re.compile(r"yyyy|yy|MMMM|MM|dd|M|d")
        parts: list[str] = []
        fields: list[str] = []
        position = 0
        for match in token_pattern.finditer(self._display_format):
            parts.append(re.escape(self._display_format[position:match.start()]))
            token = match.group()
            if token in {"yyyy", "yy"}:
                expression = r"(?P<year>[-+]?\d{1,6})"
                field = "year"
            elif token in {"MM", "M"}:
                expression = r"(?P<month>\d{1,2})"
                field = "month"
            elif token in {"dd", "d"}:
                expression = r"(?P<day>\d{1,2})"
                field = "day"
            else:
                parts.append(re.escape(token))
                position = match.end()
                continue
            if field in fields:
                self._update_text()
                return
            parts.append(expression)
            fields.append(field)
            position = match.end()
        parts.append(re.escape(self._display_format[position:]))

        match = re.fullmatch("".join(parts), self._editor.text())
        if match is None or set(fields) != {"year", "month", "day"}:
            self._update_text()
            return

        year_text = match.group("year")
        year = int(year_text)
        if not year_text.startswith(("-", "+")):
            current_era = self._calendar.era_for_year(self._date.year)
            era = self._calendar.eras.get(current_era) if current_era else None
            if era is not None and era.contains(-1):
                year = -year
        month = int(match.group("month")) - 1
        day = int(match.group("day")) - 1
        days = self._calendar.month_days(month, year)
        if days is None or not 0 <= day < days:
            self._update_text()
            return

        self.setDate(DateModel(year=year, month=month, day=day))

    def _show_calendar(self) -> None:
        if not self._calendar_popup_enabled or self._calendar is None:
            return
        popup = QWorldCalendarPopup(
            self._calendar,
            self._date,
            self,
        )
        popup.dateSelected.connect(self.setDate)
        popup.adjustSize()
        anchor = self.mapToGlobal(QPoint(self.width(), self.height()))
        popup.move(anchor.x() - popup.width(), anchor.y())
        popup.exec()


class QWorldTimeEdit(QWidget):
    timeChanged = Signal(WorldTime)

    def __init__(
        self,
        date_time: WorldTime | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._time = date_time or WorldTime(
            year=0,
            month=0,
            day=0,
            hours=0,
            minutes=0,
            seconds=0,
        )
        self._display_format = "HH:mm:ss"
        self._hour = CompactSpinBox()
        self._minute = CompactSpinBox()
        self._second = CompactSpinBox()
        self._configure_field(self._hour, 0, 23, "Hours")
        self._configure_field(self._minute, 0, 59, "Minutes")
        self._configure_field(self._second, 0, 59, "Seconds")
        self._field_values = {
            self._hour: self._hour.value(),
            self._minute: self._minute.value(),
            self._second: self._second.value(),
        }
        self._hour.valueChanged.connect(self._on_changed)
        self._minute.valueChanged.connect(self._on_changed)
        self._second.valueChanged.connect(self._on_changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        layout.addWidget(self._hour)
        layout.addWidget(self._separator())
        layout.addWidget(self._minute)
        layout.addWidget(self._separator())
        layout.addWidget(self._second)
        self._update_visibility()

    @staticmethod
    def _configure_field(spinbox: CompactSpinBox, minimum: int, maximum: int, name: str):
        spinbox.setRange(minimum, maximum)
        spinbox.spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.spinbox.setWrapping(True)
        spinbox.setAccessibleName(name)

    @staticmethod
    def _separator():
        separator = QLabel(":")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setFixedWidth(7)
        return separator

    def time(self) -> WorldTime:
        return self._time

    def setTime(self, time: WorldTime) -> None:
        self._updating = True
        try:
            self._time = time
            self._hour.setValue(time.hours)
            self._minute.setValue(time.minutes)
            self._second.setValue(time.seconds)
            self._field_values.update(
                {
                    self._hour: time.hours,
                    self._minute: time.minutes,
                    self._second: time.seconds,
                }
            )
        finally:
            self._updating = False
        self._update_visibility()

    def setDisplayFormat(self, format: str) -> None:
        self._display_format = format
        self._update_visibility()

    def displayFormat(self) -> str:
        return self._display_format

    def _on_changed(self) -> None:
        if getattr(self, "_updating", False):
            return
        spinbox = self.sender()
        previous_value = self._field_values[spinbox]
        current_value = spinbox.value()
        self._field_values[spinbox] = current_value

        if spinbox is self._hour:
            minimum, maximum = 0, 23
            delta = WorldTimeDelta(hours=self._wrapped_delta(
                previous_value, current_value, minimum, maximum
            ))
        elif spinbox is self._minute:
            minimum, maximum = 0, 59
            delta = WorldTimeDelta(minutes=self._wrapped_delta(
                previous_value, current_value, minimum, maximum
            ))
        else:
            minimum, maximum = 0, 59
            delta = WorldTimeDelta(seconds=self._wrapped_delta(
                previous_value, current_value, minimum, maximum
            ))

        self._time = self._time.advance(delta)
        self.setTime(self._time)
        self.timeChanged.emit(self._time)

    @staticmethod
    def _wrapped_delta(previous: int, current: int, minimum: int, maximum: int) -> int:
        if previous == maximum and current == minimum:
            return 1
        if previous == minimum and current == maximum:
            return -1
        return current - previous

    def _update_visibility(self) -> None:
        self._hour.setVisible("H" in self._display_format or "h" in self._display_format)
        self._minute.setVisible("m" in self._display_format)
        self._second.setVisible("s" in self._display_format)