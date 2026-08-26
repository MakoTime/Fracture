from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LeapRule:
    divisor: int
    remainder: int
    exception_divisor: int
    month_id: str

    def to_dict(self) -> dict:
        return {
            "divisor": self.divisor,
            "remainder": self.remainder,
            "exception_divisor": self.exception_divisor,
            "month_id": self.month_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LeapRule":
        return cls(
            divisor=data["divisor"],
            remainder=data["remainder"],
            exception_divisor=data["exception_divisor"],
            month_id=data["month_id"],
        )


@dataclass(frozen=True)
class DayLength:
    hours: int
    minutes: int
    seconds: int

    @property
    def total_seconds(self) -> int:
        return (
            self.hours * 60 * 60
            + self.minutes * 60
            + self.seconds
        )

    def to_dict(self) -> dict:
        return {
            "hours": self.hours,
            "minutes": self.minutes,
            "seconds": self.seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DayLength":
        return cls(
            hours=data["hours"],
            minutes=data["minutes"],
            seconds=data["seconds"],
        )


@dataclass(frozen=True)
class Month:
    id: str
    name: str
    days: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "days": self.days,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Month":
        return cls(
            id=data["id"],
            name=data["name"],
            days=data["days"],
        )


@dataclass(frozen=True)
class Season:
    id: str
    name: str
    month_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "month_ids": list(self.month_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Season":
        return cls(
            id=data["id"],
            name=data["name"],
            month_ids=tuple(data["month_ids"]),
        )


@dataclass(frozen=True)
class CalendarEpoch:
    datetime: datetime
    year: int = 0
    month: int = 0
    day: int = 0

    def to_dict(self) -> dict:
        return {
            "datetime": self.datetime.isoformat(),
            "year": self.year,
            "month": self.month,
            "day": self.day,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalendarEpoch":
        return cls(
            datetime=datetime.fromisoformat(data["datetime"]),
            year=data["year"],
            month=data["month"],
            day=data["day"],
        )


@dataclass(frozen=True)
class Era:
    start: int | None = None
    end: int | None = None

    def __post_init__(self) -> None:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("Era start cannot be after its end.")

    def contains(self, year: int) -> bool:
        return (
            (self.start is None or year >= self.start)
            and (self.end is None or year <= self.end)
        )

    def to_list(self) -> list[int | None]:
        return [self.start, self.end]

    @classmethod
    def from_value(cls, value: list[int | None] | tuple[int | None, int | None]) -> "Era":
        if len(value) != 2:
            raise ValueError("An era must have exactly two bounds.")
        return cls(start=value[0], end=value[1])
        

@dataclass(frozen=True)
class DateModel:
    year: int
    month: int
    day: int
    
    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DateModel":
        return cls(
            year=data["year"],
            month=data["month"],
            day=data["day"],
        )


@dataclass(frozen=True)
class Calendar:
    day_length: DayLength
    weekdays: tuple[str, ...]
    seasons: tuple[Season, ...]
    months: tuple[Month, ...]
    eras: dict[str, Era]
    epoch: CalendarEpoch
    leap_rule: LeapRule | None = None

    def __post_init__(self) -> None:
        if self.eras and not any(era.contains(-1) for era in self.eras.values()):
            raise ValueError("Calendar must define an era that covers negative years.")

    @property
    def month_count(self) -> int:
        return len(self.months)

    @property
    def season_count(self) -> int:
        return len(self.seasons)

    def get_month(self, month: int) -> Month | None:
        if not 0 <= month < self.month_count:
            return None

        return self.months[month]

    def get_month_by_id(self, month_id: str) -> Month | None:
        for month in self.months:
            if month.id == month_id:
                return month

        return None

    def get_month_number(self, month_id: str) -> int | None:
        for index, month in enumerate(self.months):
            if month.id == month_id:
                return index

        return None

    def get_month_by_name(self, name: str) -> Month | None:
        for month in self.months:
            if month.name == name:
                return month

        return None

    def get_season(self, month: int) -> Season | None:
        month_ref = self.get_month(month)

        if month_ref is None:
            return None

        for season in self.seasons:
            if month_ref.id in season.month_ids:
                return season

        return None

    def get_season_for_month(self, month_id: str) -> Season | None:
        for season in self.seasons:
            if month_id in season.month_ids:
                return season

        return None

    def era_for_year(self, year: int) -> str | None:
        for name, era in self.eras.items():
            if era.contains(year):
                return name

        return None

    def is_leap_year(self, year: int) -> bool:
        if self.leap_rule is None:
            return False

        rule = self.leap_rule

        return (
            year % rule.divisor == rule.remainder
            and year % rule.exception_divisor != 0
        )

    def month_days(self, month: int, year: int) -> int | None:
        month_ref = self.get_month(month)

        if month_ref is None:
            return None

        days = month_ref.days

        if (
            self.leap_rule is not None
            and month_ref.id == self.leap_rule.month_id
            and self.is_leap_year(year)
        ):
            days += 1

        return days

    def to_dict(self) -> dict:
        return {
            "day_length": self.day_length.to_dict(),
            "weekdays": list(self.weekdays),
            "seasons": [
                season.to_dict()
                for season in self.seasons
            ],
            "months": [
                month.to_dict()
                for month in self.months
            ],
            "eras": {
                name: era.to_list()
                for name, era in self.eras.items()
            },
            "epoch": self.epoch.to_dict(),
            "leap_rule": (
                self.leap_rule.to_dict()
                if self.leap_rule is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Calendar":
        return cls(
            day_length=DayLength.from_dict(data["day_length"]),
            weekdays=tuple(data["weekdays"]),
            seasons=tuple(
                Season.from_dict(season)
                for season in data["seasons"]
            ),
            months=tuple(
                Month.from_dict(month)
                for month in data["months"]
            ),
            eras={
                name: Era.from_value(value)
                for name, value in data["eras"].items()
            },
            epoch=CalendarEpoch.from_dict(data["epoch"]),
            leap_rule=(
                LeapRule.from_dict(data["leap_rule"])
                if data["leap_rule"] is not None
                else None
            ),
        )

DEFAULT_CALENDAR = Calendar(
    day_length=DayLength(hours=24, minutes=0, seconds=0),
    weekdays=tuple("Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()),
    seasons=(
        Season(id=0, name="Summer", month_ids=("December", "January", "February")),
        Season(id=1, name="Autumn", month_ids=("March", "April", "May")),
        Season(id=2, name="Winter", month_ids=("June", "July", "August")),
        Season(id=3, name="Spring", month_ids=("September", "October", "November")),
    ),
    months=(
        Month(id=0, name="January", days=31),
        Month(id=1, name="February", days=28),
        Month(id=2, name="March", days=31),
        Month(id=3, name="April", days=30),
        Month(id=4, name="May", days=31),
        Month(id=5, name="June", days=30),
        Month(id=6, name="July", days=31),
        Month(id=7, name="August", days=31),
        Month(id=8, name="September", days=30),
        Month(id=9, name="October", days=31),
        Month(id=10, name="November", days=30),
        Month(id=11, name="December", days=31),
    ),
    eras={"BCE": Era(None, -1)},
    epoch=DateModel(year=0, month=0, day=0),
    leap_rule=LeapRule(divisor=4, remainder=0, exception_divisor=100, month_id="February"),
)