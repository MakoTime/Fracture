import unittest
from datetime import datetime, timezone

from src.common.calendar import (
    Calendar,
    CalendarEpoch,
    DayLength,
    DateModel,
    Era,
    LeapRule,
    Month,
    Season,
)


class TestCalendar(unittest.TestCase):
    def setUp(self):
        self.january = Month("jan", "January", 31)
        self.february = Month("feb", "February", 28)
        self.march = Month("mar", "March", 31)
        self.april = Month("apr", "April", 30)

        self.calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=(
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ),
            seasons=(
                Season(
                    "spring",
                    "Spring",
                    ("mar", "apr"),
                ),
            ),
            months=(
                self.january,
                self.february,
                self.march,
                self.april,
            ),
            eras={},
            epoch=CalendarEpoch(
                datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
            ),
        )

    def test_month_count(self):
        self.assertEqual(self.calendar.month_count, 4)

    def test_season_count(self):
        self.assertEqual(self.calendar.season_count, 1)

    def test_month_order_is_tuple_order(self):
        self.assertIs(
            self.calendar.months[0],
            self.january,
        )
        self.assertIs(
            self.calendar.months[1],
            self.february,
        )
        self.assertIs(
            self.calendar.months[2],
            self.march,
        )

    def test_get_month_uses_zero_based_calendar_index(self):
        self.assertEqual(
            self.calendar.get_month(0),
            self.january,
        )
        self.assertEqual(
            self.calendar.get_month(1),
            self.february,
        )
        self.assertEqual(
            self.calendar.get_month(2),
            self.march,
        )

    def test_get_month_rejects_negative_index(self):
        self.assertIsNone(
            self.calendar.get_month(-1)
        )

    def test_get_month_rejects_index_after_last_month(self):
        self.assertIsNone(
            self.calendar.get_month(4)
        )

    def test_get_month_by_id(self):
        self.assertEqual(
            self.calendar.get_month_by_id("mar"),
            self.march,
        )

    def test_get_month_by_id_returns_none_for_unknown_id(self):
        self.assertIsNone(
            self.calendar.get_month_by_id("unknown")
        )

    def test_get_month_number(self):
        self.assertEqual(
            self.calendar.get_month_number("jan"),
            0,
        )
        self.assertEqual(
            self.calendar.get_month_number("mar"),
            2,
        )

    def test_get_month_number_returns_none_for_unknown_id(self):
        self.assertIsNone(
            self.calendar.get_month_number("unknown")
        )

    def test_get_month_by_name(self):
        self.assertEqual(
            self.calendar.get_month_by_name("March"),
            self.march,
        )

    def test_get_month_by_name_returns_none_for_unknown_name(self):
        self.assertIsNone(
            self.calendar.get_month_by_name("December")
        )

    def test_get_season_for_month(self):
        season = self.calendar.get_season_for_month("mar")

        self.assertIsNotNone(season)
        self.assertEqual(season.name, "Spring")

    def test_get_season_for_month_returns_none(self):
        self.assertIsNone(
            self.calendar.get_season_for_month("jan")
        )

    def test_get_season_by_month_number(self):
        season = self.calendar.get_season(2)

        self.assertIsNotNone(season)
        self.assertEqual(season.name, "Spring")

    def test_get_season_returns_none_for_invalid_month(self):
        self.assertIsNone(
            self.calendar.get_season(99)
        )

    def test_month_days(self):
        self.assertEqual(
            self.calendar.month_days(0, 0),
            31,
        )
        self.assertEqual(
            self.calendar.month_days(1, 0),
            28,
        )
        self.assertEqual(
            self.calendar.month_days(2, 0),
            31,
        )
        self.assertEqual(
            self.calendar.month_days(3, 0),
            30,
        )

    def test_month_days_returns_none_for_invalid_month(self):
        self.assertIsNone(
            self.calendar.month_days(99, 0)
        )

    def test_day_total_seconds(self):
        day_length = DayLength(24, 0, 0)

        self.assertEqual(
            day_length.total_seconds,
            86400,
        )

    def test_day_total_seconds_with_minutes_and_seconds(self):
        day_length = DayLength(1, 30, 15)

        self.assertEqual(
            day_length.total_seconds,
            5415,
        )

    def test_era_bounds_round_trip_through_serialization(self):
        calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Monday",),
            seasons=(),
            months=(self.january,),
            eras={"BCE": Era(None, -1), "Future": Era(3500, None)},
            epoch=CalendarEpoch(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                year=0,
            ),
        )

        restored = Calendar.from_dict(calendar.to_dict())

        self.assertEqual(restored.eras, calendar.eras)

    def test_calendar_requires_an_era_covering_negative_years(self):
        with self.assertRaises(ValueError):
            Calendar(
                day_length=DayLength(24, 0, 0),
                weekdays=("Monday",),
                seasons=(),
                months=(self.january,),
                eras={"Future": Era(3500, None)},
                epoch=CalendarEpoch(datetime(2026, 1, 1, tzinfo=timezone.utc)),
            )

    def test_legacy_closed_era_values_are_deserialized(self):
        calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Monday",),
            seasons=(),
            months=(self.january,),
            eras={"BCE": Era(None, -1), "Common": Era(1, 3500)},
            epoch=CalendarEpoch(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )

        data = calendar.to_dict()
        data["eras"] = {"BCE": [None, -1], "Common": [1, 3500]}

        restored = Calendar.from_dict(data)

        self.assertEqual(restored.eras["Common"], Era(1, 3500))


class TestCalendarLeapYears(unittest.TestCase):
    def setUp(self):
        self.february = Month(
            "feb",
            "February",
            28,
        )

        self.calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Monday",),
            seasons=(),
            months=(
                self.february,
            ),
            eras={},
            epoch=CalendarEpoch(
                datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
            ),
            leap_rule=LeapRule(
                divisor=4,
                remainder=0,
                exception_divisor=100,
                month_id="feb",
            ),
        )

    def test_leap_year(self):
        self.assertTrue(
            self.calendar.is_leap_year(4)
        )

    def test_non_leap_year(self):
        self.assertFalse(
            self.calendar.is_leap_year(5)
        )

    def test_exception_year_is_not_leap_year(self):
        self.assertFalse(
            self.calendar.is_leap_year(100)
        )

    def test_leap_year_exception_can_be_overridden(self):
        calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Monday",),
            seasons=(),
            months=(self.february,),
            eras={},
            epoch=self.calendar.epoch,
            leap_rule=LeapRule(
                divisor=4,
                remainder=0,
                exception_divisor=100,
                month_id="feb",
            ),
        )

        self.assertTrue(
            calendar.is_leap_year(104)
        )

    def test_leap_year_adds_day_to_configured_month(self):
        self.assertEqual(
            self.calendar.month_days(0, 4),
            29,
        )

    def test_non_leap_year_does_not_add_day(self):
        self.assertEqual(
            self.calendar.month_days(0, 5),
            28,
        )


class TestCalendarImmutability(unittest.TestCase):
    def test_month_is_frozen(self):
        month = Month(
            "jan",
            "January",
            31,
        )

        with self.assertRaises(AttributeError):
            month.name = "Not January"

    def test_calendar_is_frozen(self):
        calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Monday",),
            seasons=(),
            months=(),
            eras={},
            epoch=CalendarEpoch(
                datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
            ),
        )

        with self.assertRaises(AttributeError):
            calendar.months = ()
