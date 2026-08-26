from __future__ import annotations
import logging

from dataclasses import dataclass

from .manager import CalendarManager
from .model import Calendar, DateModel

Logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class WorldTimeDelta:
    seconds: int = 0
    minutes: int = 0
    hours: int = 0
    days: int = 0
    months: int = 0
    years: int = 0
    milliseconds: float = 0.0
    
    @property
    def calendar(self) -> Calendar:
        return WorldClock.calendar()
    
    def total_seconds(self) -> float:
        minute_multiplier = 60
        hour_multiplier = 60 * minute_multiplier
        day_multiplier = self.calendar.day_length.total_seconds
        calendar_days = sum(
            month.days
            for month in self.calendar.months
        )
        month_multiplier = calendar_days * day_multiplier
        year_multiplier = month_multiplier
        return (
            self.seconds
            + self.milliseconds / 1000
            + self.minutes * minute_multiplier
            + self.hours * hour_multiplier
            + self.days * day_multiplier
            + self.months * month_multiplier
            + self.years * year_multiplier
        )
    


@dataclass(frozen=True)
class WorldTime:
    year: int
    month: int
    day: int
    hours: int
    minutes: int
    seconds: int
    milliseconds: int = 0

    @classmethod
    def now(cls) -> "WorldTime":
        return WorldClock.now()

    @classmethod
    def from_dict(cls, data: dict) -> "WorldTime":
        return cls(
            year=data["year"],
            month=data["month"],
            day=data["day"],
            hours=data["hours"],
            minutes=data["minutes"],
            seconds=data["seconds"],
            milliseconds=data.get("milliseconds", 0),
        )

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "hours": self.hours,
            "minutes": self.minutes,
            "seconds": self.seconds,
            "milliseconds": self.milliseconds,
        }
        
    @property
    def calendar(self) -> Calendar | None:
        return WorldClock.calendar()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, WorldTime):
            return NotImplemented
        return self._total_seconds() < other._total_seconds()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, WorldTime):
            return NotImplemented
        return self._total_seconds() <= other._total_seconds()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, WorldTime):
            return NotImplemented
        return self._total_seconds() > other._total_seconds()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, WorldTime):
            return NotImplemented
        return self._total_seconds() >= other._total_seconds()

    def __sub__(
        self,
        other: object,
    ) -> WorldTimeDelta:
        if not isinstance(other, WorldTime):
            return NotImplemented

        return WorldTimeDelta(
            seconds=self._total_seconds() - other._total_seconds()
        )

    def __add__(self, delta: WorldTimeDelta) -> "WorldTime":
        if not isinstance(delta, WorldTimeDelta):
            return NotImplemented

        return WorldClock.add_delta(self, delta)
    
    @staticmethod
    def join_date_time(date: DateModel, time: WorldTime) -> WorldTime:
        return WorldTime(
            year=date.year,
            month=date.month,
            day=date.day,
            hours=time.hours,
            minutes=time.minutes,
            seconds=time.seconds,
        )
        
    def advance(
        self,
        delta: WorldTimeDelta,
    ) -> "WorldTime":
        calendar = self.calendar
        day_length = calendar.day_length.total_seconds
        if day_length <= 0:
            raise RuntimeError(
                "Calendar day must contain at least one second."
            )

        year = self.year
        month = self.month
        day = self.day
        month_offset = delta.years * calendar.month_count + delta.months
        if month_offset:
            month_index = year * calendar.month_count + month + month_offset
            year, month = divmod(month_index, calendar.month_count)
            month_days = calendar.month_days(month, year)
            if month_days is None:
                raise RuntimeError("Invalid calendar month.")
            day = min(day, month_days - 1)

        current_seconds = (
            self.hours * 60 * 60
            + self.minutes * 60
            + self.seconds
            + self.milliseconds / 1000
        )
        total_seconds = current_seconds + (
            delta.seconds
            + delta.milliseconds / 1000
            + delta.minutes * 60
            + delta.hours * 60 * 60
            + delta.days * day_length
        )
        day_delta, seconds = divmod(
            total_seconds,
            day_length,
        )
        day_delta = int(day_delta)
        if day_delta > 0:
            while day_delta > 0:
                month_days = calendar.month_days(month, year)
                if month_days is None:
                    raise RuntimeError("Invalid calendar month.")
                remaining = month_days - day - 1
                if day_delta <= remaining:
                    day += day_delta
                    day_delta = 0
                    break
                day_delta -= remaining + 1
                day = 0
                month += 1
                if month >= calendar.month_count:
                    month = 0
                    year += 1
        elif day_delta < 0:
            while day_delta < 0:
                if day + day_delta >= 0:
                    day += day_delta
                    day_delta = 0
                    break
                day_delta += day + 1
                month -= 1
                if month < 0:
                    month = calendar.month_count - 1
                    year -= 1
                month_days = calendar.month_days(month, year)
                if month_days is None:
                    raise RuntimeError("Invalid calendar month.")
                day = month_days - 1
        hours, seconds = divmod(
            int(seconds),
            60 * 60,
        )
        minutes, seconds = divmod(
            seconds,
            60,
        )
        milliseconds = round((total_seconds % 1) * 1000)
        if milliseconds == 1000:
            seconds += 1
            milliseconds = 0
        if seconds >= 60:
            minutes, seconds = divmod(seconds, 60)
        if minutes >= 60:
            hours, minutes = divmod(minutes, 60)
        return WorldTime(
            year=year,
            month=month,
            day=day,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
        )

    def _total_seconds(self) -> int:
        return WorldClock._day_offset(self) * self.calendar.day_length.total_seconds + (
            self.hours * 60 * 60
            + self.minutes * 60
            + self.seconds
            + self.milliseconds / 1000
        )


class WorldClock:
    _manager: CalendarManager | None = None
    _current: WorldTime | None = None

    @classmethod
    def configure(
        cls,
        manager: CalendarManager,
        current: WorldTime | None = None,
    ) -> None:
        cls._manager = manager
        cls._current = current

    @classmethod
    def manager(cls) -> CalendarManager:
        if cls._manager is None:
            Logger.error("No calendar is configured. Loading default calendar.")
            cls._manager = CalendarManager()
            cls._manager.load_default_calendar()

        return cls._manager

    @classmethod
    def calendar(cls) -> Calendar:
        calendar = cls.manager().calendar

        if calendar is None:
            Logger.error("No calendar is configured. Loading default calendar.")
            cls.manager().load_default_calendar()

        return calendar

    @classmethod
    def now(cls) -> WorldTime:
        if cls._current is None:
            Logger.error("World clock has no current time. Returning epoch time.")
            cls._current = cls._as_default_epoch()
            # raise RuntimeError("World clock has no current time.")

        return cls._current
    
    @classmethod
    def _as_default_epoch(cls) -> WorldTime:
        epoch = cls.calendar().epoch
        return WorldTime(
            year=epoch.year,
            month=epoch.month,
            day=epoch.day,
            hours=0,
            minutes=0,
            seconds=0,
        )

    @classmethod
    def set(cls, time: WorldTime) -> WorldTime:
        cls._current = time
        return time

    @classmethod
    def advance(cls, delta: WorldTimeDelta) -> WorldTime:
        cls._current = cls.add_delta(cls.now(), delta)
        return cls._current
    
    @classmethod
    def compare(
        cls,
        left: WorldTime,
        right: WorldTime,
    ) -> int:
        left_day = cls._day_offset(left)
        right_day = cls._day_offset(right)

        if left_day < right_day:
            return -1

        if left_day > right_day:
            return 1

        left_seconds = (
            left.hours * 3600
            + left.minutes * 60
            + left.seconds
        )

        right_seconds = (
            right.hours * 3600
            + right.minutes * 60
            + right.seconds
        )

        return (left_seconds > right_seconds) - (
            left_seconds < right_seconds
        )

    @classmethod
    def add_delta(
        cls,
        time: WorldTime,
        delta: WorldTimeDelta,
    ) -> WorldTime:
        return time.advance(delta)

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "calendar": cls.manager().to_dict(),
            "time": cls.now().to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorldTime:
        manager = CalendarManager.from_dict(data["calendar"])
        current = WorldTime.from_dict(data["time"])

        cls.configure(manager, current)

        return current

    @classmethod
    def _date_from_day_offset(
        cls,
        offset: int,
    ) -> DateModel:
        calendar = cls.calendar()

        year = calendar.epoch.year
        month = calendar.epoch.month
        day = calendar.epoch.day

        if offset >= 0:
            while offset:
                month_days = calendar.month_days(month, year)

                if month_days is None:
                    raise RuntimeError("Invalid calendar month.")

                remaining = month_days - day

                if offset < remaining:
                    day += offset
                    offset = 0
                    break

                offset -= remaining
                day = 0
                month += 1

                if month >= calendar.month_count:
                    month = 0
                    year += 1
        else:
            while offset < 0:
                if day + offset >= 0:
                    day += offset
                    offset = 0
                    break

                offset += day
                month -= 1

                if month < 0:
                    month = calendar.month_count - 1
                    year -= 1

                month_days = calendar.month_days(month, year)

                if month_days is None:
                    raise RuntimeError("Invalid calendar month.")

                day = month_days - 1

        return DateModel(
            year=year,
            month=month,
            day=day,
        )

    @classmethod
    def _day_offset(cls, time: WorldTime) -> int:
        calendar = cls.calendar()

        year = calendar.epoch.year
        month = calendar.epoch.month
        day = calendar.epoch.day
        offset = 0

        while year < time.year or (
            year == time.year and month < time.month
        ):
            month_days = calendar.month_days(month, year)

            if month_days is None:
                raise RuntimeError("Invalid calendar month.")

            offset += month_days
            month += 1

            if month >= calendar.month_count:
                month = 0
                year += 1

        while year > time.year or (
            year == time.year and month > time.month
        ):
            month -= 1
            if month < 0:
                month = calendar.month_count - 1
                year -= 1
            month_days = calendar.month_days(month, year)
            if month_days is None:
                raise RuntimeError("Invalid calendar month.")
            offset -= month_days

        offset += time.day - day

        return offset