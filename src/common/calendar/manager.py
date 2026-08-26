from .builder import CalendarBuilder
from .model import Calendar, DayLength, LeapRule, Month, Season


class CalendarManager:
    def __init__(self, calendar: Calendar | None = None):
        self._calendar = calendar
        self._history: list[Calendar] = []
        self._future: list[Calendar] = []
        
    def to_dict(self) -> dict:
        return self._require_calendar().to_dict()

    def load_dict(self, data: dict) -> Calendar:
        calendar = Calendar.from_dict(data)
        self.replace(calendar)
        return calendar

    @property
    def calendar(self) -> Calendar | None:
        return self._calendar

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    @property
    def can_redo(self) -> bool:
        return bool(self._future)

    def create(self) -> Calendar:
        self._calendar = Calendar(
            day_length=DayLength(0, 0, 0),
            weekdays=(),
            seasons=(),
            months=(),
            eras={},
            epoch=None,
            leap_rule=None,
        )
        self._history.clear()
        self._future.clear()
        return self._calendar

    def replace(self, calendar: Calendar) -> None:
        self._calendar = calendar
        self._history.clear()
        self._future.clear()

    def undo(self) -> Calendar | None:
        if not self._history:
            return self._calendar

        if self._calendar is not None:
            self._future.append(self._calendar)

        self._calendar = self._history.pop()
        return self._calendar

    def redo(self) -> Calendar | None:
        if not self._future:
            return self._calendar

        if self._calendar is not None:
            self._history.append(self._calendar)

        self._calendar = self._future.pop()
        return self._calendar

    def add_month(
        self,
        name: str,
        days: int,
        index: int | None = None,
    ) -> str:
        builder = self._begin_edit()
        builder.add_month(
            Month(
                id="",
                name=name,
                days=days,
            ),
            index,
        )

        month_id = builder._months[-1].id if index is None else builder._months[index].id

        self._commit(builder)

        return month_id

    def remove_month(self, month_id: str) -> None:
        builder = self._begin_edit()
        builder.remove_month(month_id)
        self._commit(builder)

    def rename_month(
        self,
        month_id: str,
        name: str,
    ) -> None:
        builder = self._begin_edit()
        builder.rename_month(month_id, name)
        self._commit(builder)

    def set_month_days(
        self,
        month_id: str,
        days: int,
    ) -> None:
        builder = self._begin_edit()
        builder.set_month_days(month_id, days)
        self._commit(builder)

    def move_month(
        self,
        month_id: str,
        new_index: int,
    ) -> None:
        builder = self._begin_edit()
        builder.move_month(month_id, new_index)
        self._commit(builder)

    def add_season(
        self,
        name: str,
        month_ids: tuple[str, ...] = (),
    ) -> str:
        builder = self._begin_edit()
        builder.add_season(
            Season(
                id="",
                name=name,
                month_ids=month_ids,
            )
        )

        season_id = builder._seasons[-1].id

        self._commit(builder)

        return season_id

    def remove_season(self, season_id: str) -> None:
        builder = self._begin_edit()
        builder.remove_season(season_id)
        self._commit(builder)

    def rename_season(
        self,
        season_id: str,
        name: str,
    ) -> None:
        builder = self._begin_edit()
        builder.rename_season(season_id, name)
        self._commit(builder)

    def set_season_months(
        self,
        season_id: str,
        month_ids: tuple[str, ...],
    ) -> None:
        builder = self._begin_edit()
        builder.set_season_months(season_id, month_ids)
        self._commit(builder)

    def set_leap_rule(
        self,
        divisor: int,
        remainder: int,
        exception_divisor: int,
        month_id: str,
    ) -> None:
        builder = self._begin_edit()
        builder.set_leap_rule(
            LeapRule(
                divisor=divisor,
                remainder=remainder,
                exception_divisor=exception_divisor,
                month_id=month_id,
            )
        )
        self._commit(builder)

    def remove_leap_rule(self) -> None:
        builder = self._begin_edit()
        builder.remove_leap_rule()
        self._commit(builder)

    def _require_calendar(self) -> Calendar:
        if self._calendar is None:
            raise RuntimeError("No calendar is loaded.")
        return self._calendar

    def _begin_edit(self) -> CalendarBuilder:
        return CalendarBuilder.from_calendar(
            self._require_calendar()
        )

    def _commit(self, builder: CalendarBuilder) -> None:
        if self._calendar is not None:
            self._history.append(self._calendar)

        self._calendar = builder.build()
        self._future.clear()
        
    def load_default_calendar(self) -> Calendar:
        from .model import DEFAULT_CALENDAR

        self._calendar = DEFAULT_CALENDAR
        self._history.append(self._calendar)
        self._future.clear()

        return self._calendar
