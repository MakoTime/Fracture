from .model import (
    Calendar,
    CalendarEpoch,
    DayLength,
    Era,
    LeapRule,
    Month,
    Season,
)


class CalendarBuilder:
    def __init__(self):
        self._day_length: DayLength | None = None
        self._epoch: CalendarEpoch | None = None
        self._weekdays: list[str] = []
        self._seasons: list[Season] = []
        self._months: list[Month] = []
        self._eras: dict[str, Era] = {}
        self._leap_rule: LeapRule | None = None

    @classmethod
    def from_calendar(cls, calendar: Calendar) -> "CalendarBuilder":
        builder = cls()
        builder._day_length = calendar.day_length
        builder._epoch = calendar.epoch
        builder._weekdays = list(calendar.weekdays)
        builder._seasons = list(calendar.seasons)
        builder._months = list(calendar.months)
        builder._eras = dict(calendar.eras)
        builder._leap_rule = calendar.leap_rule
        return builder

    def set_day_length(self, day_length: DayLength) -> "CalendarBuilder":
        if day_length.total_seconds <= 0:
            raise ValueError("Day length must contain at least one second.")
        self._day_length = day_length
        return self

    def set_epoch(self, epoch: CalendarEpoch) -> "CalendarBuilder":
        self._epoch = epoch
        return self

    def set_weekdays(self, weekdays: tuple[str, ...]) -> "CalendarBuilder":
        if len(set(weekdays)) != len(weekdays):
            raise ValueError("Duplicate weekdays are not allowed.")
        self._weekdays = list(weekdays)
        return self

    def add_weekday(self, name: str) -> "CalendarBuilder":
        if name in self._weekdays:
            raise ValueError(f"Weekday already exists: {name}")
        self._weekdays.append(name)
        return self

    def remove_weekday(self, name: str) -> "CalendarBuilder":
        if name not in self._weekdays:
            raise ValueError(f"Weekday does not exist: {name}")
        self._weekdays.remove(name)
        return self

    def rename_weekday(
        self,
        old_name: str,
        new_name: str,
    ) -> "CalendarBuilder":
        if old_name not in self._weekdays:
            raise ValueError(f"Weekday does not exist: {old_name}")
        if new_name in self._weekdays:
            raise ValueError(f"Weekday already exists: {new_name}")
        index = self._weekdays.index(old_name)
        self._weekdays[index] = new_name
        return self

    def add_month(
        self,
        month: Month,
        index: int | None = None,
    ) -> "CalendarBuilder":
        if month.days < 1:
            raise ValueError("Month must contain at least one day.")

        if any(existing.id == month.id for existing in self._months):
            raise ValueError(f"Month ID already exists: {month.id}")

        if any(existing.name == month.name for existing in self._months):
            raise ValueError(f"Month already exists: {month.name}")

        if index is None:
            self._months.append(month)
        else:
            if not 0 <= index <= len(self._months):
                raise IndexError("Invalid month insertion index.")
            self._months.insert(index, month)

        return self

    def remove_month(self, month_id: str) -> "CalendarBuilder":
        month = self._get_month(month_id)
        self._months.remove(month)

        self._seasons = [
            Season(
                id=season.id,
                name=season.name,
                month_ids=tuple(
                    mid
                    for mid in season.month_ids
                    if mid != month_id
                ),
            )
            for season in self._seasons
        ]

        if (
            self._leap_rule is not None
            and self._leap_rule.month_id == month_id
        ):
            self._leap_rule = None

        return self

    def rename_month(
        self,
        month_id: str,
        name: str,
    ) -> "CalendarBuilder":
        month = self._get_month(month_id)

        if any(
            other.id != month_id and other.name == name
            for other in self._months
        ):
            raise ValueError(f"Month already exists: {name}")

        index = self._months.index(month)

        self._months[index] = Month(
            id=month.id,
            name=name,
            days=month.days,
        )

        return self

    def set_month_days(
        self,
        month_id: str,
        days: int,
    ) -> "CalendarBuilder":
        if days < 1:
            raise ValueError("Month must contain at least one day.")

        month = self._get_month(month_id)
        index = self._months.index(month)

        self._months[index] = Month(
            id=month.id,
            name=month.name,
            days=days,
        )

        return self

    def move_month(
        self,
        month_id: str,
        new_index: int,
    ) -> "CalendarBuilder":
        if not 0 <= new_index < len(self._months):
            raise IndexError("Invalid month position.")

        month = self._get_month(month_id)

        self._months.remove(month)
        self._months.insert(new_index, month)

        return self

    def add_season(self, season: Season) -> "CalendarBuilder":
        if any(existing.id == season.id for existing in self._seasons):
            raise ValueError(f"Season ID already exists: {season.id}")

        if any(existing.name == season.name for existing in self._seasons):
            raise ValueError(f"Season already exists: {season.name}")

        self._seasons.append(season)
        return self

    def remove_season(self, season_id: str) -> "CalendarBuilder":
        season = self._get_season(season_id)
        self._seasons.remove(season)
        return self

    def rename_season(
        self,
        season_id: str,
        name: str,
    ) -> "CalendarBuilder":
        season = self._get_season(season_id)

        if any(
            other.id != season_id and other.name == name
            for other in self._seasons
        ):
            raise ValueError(f"Season already exists: {name}")

        index = self._seasons.index(season)

        self._seasons[index] = Season(
            id=season.id,
            name=name,
            month_ids=season.month_ids,
        )

        return self

    def set_season_months(
        self,
        season_id: str,
        month_ids: tuple[str, ...],
    ) -> "CalendarBuilder":
        season = self._get_season(season_id)
        index = self._seasons.index(season)

        self._seasons[index] = Season(
            id=season.id,
            name=season.name,
            month_ids=month_ids,
        )

        return self

    def set_leap_rule(
        self,
        rule: LeapRule,
    ) -> "CalendarBuilder":
        if rule.divisor == 0:
            raise ValueError("Divisor cannot be zero.")

        if rule.exception_divisor == 0:
            raise ValueError("Exception divisor cannot be zero.")

        self._leap_rule = rule
        return self

    def remove_leap_rule(self) -> "CalendarBuilder":
        self._leap_rule = None
        return self

    def add_era(
        self,
        name: str,
        start: int | None = None,
        end: int | None = None,
    ) -> "CalendarBuilder":
        if name in self._eras:
            raise ValueError(f"Era already exists: {name}")

        if start is not None and end is not None and start > end:
            raise ValueError("Era start cannot be after its end.")

        self._eras[name] = Era(start=start, end=end)
        return self

    def remove_era(self, name: str) -> "CalendarBuilder":
        if name not in self._eras:
            raise ValueError(f"Era does not exist: {name}")

        del self._eras[name]
        return self

    def build(self) -> Calendar:
        return Calendar(
            day_length=self._day_length,
            weekdays=tuple(self._weekdays),
            seasons=tuple(self._seasons),
            months=tuple(self._months),
            eras=dict(self._eras),
            epoch=self._epoch,
            leap_rule=self._leap_rule,
        )

    def _get_month(self, month_id: str) -> Month:
        for month in self._months:
            if month.id == month_id:
                return month

        raise ValueError(f"Month does not exist: {month_id}")

    def _get_season(self, season_id: str) -> Season:
        for season in self._seasons:
            if season.id == season_id:
                return season

        raise ValueError(f"Season does not exist: {season_id}")
