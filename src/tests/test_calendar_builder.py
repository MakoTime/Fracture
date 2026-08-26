import unittest
from datetime import datetime, timezone

from src.common.calendar import CalendarBuilder, DayLength, Era, Month, Season, LeapRule


class TestCalendarBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = CalendarBuilder()

    def test_build_blank_calendar(self):
        calendar = self.builder.build()

        self.assertIsNotNone(calendar)
        self.assertEqual(calendar.month_count, 0)
        self.assertEqual(calendar.season_count, 0)
        self.assertEqual(calendar.weekdays, ())
        self.assertEqual(calendar.eras, {})
        self.assertIsNone(calendar.leap_rule)

    def test_set_day(self):
        self.builder.set_day_length(
            DayLength(24, 0, 0)
        )

        calendar = self.builder.build()

        self.assertEqual(
            calendar.day_length,
            DayLength(24, 0, 0),
        )

    def test_add_month(self):
        month = Month(
            "jan",
            "January",
            31,
        )

        self.builder.add_month(month)

        calendar = self.builder.build()

        self.assertEqual(
            calendar.month_count,
            1,
        )
        self.assertEqual(
            calendar.get_month(0),
            month,
        )

    def test_month_order_is_preserved(self):
        january = Month("jan", "January", 31)
        february = Month("feb", "February", 28)
        march = Month("mar", "March", 31)

        self.builder.add_month(january)
        self.builder.add_month(february)
        self.builder.add_month(march)

        calendar = self.builder.build()

        self.assertEqual(
            calendar.months,
            (
                january,
                february,
                march,
            ),
        )

    def test_add_era_allows_open_ended_bounds(self):
        self.builder.add_era("BCE", None, -1)
        self.builder.add_era("Future", 3500, None)

        calendar = self.builder.build()

        self.assertEqual(calendar.eras["BCE"], Era(None, -1))
        self.assertEqual(calendar.eras["Future"], Era(3500, None))
        self.assertTrue(calendar.eras["BCE"].contains(-100))
        self.assertFalse(calendar.eras["BCE"].contains(0))
        self.assertTrue(calendar.eras["Future"].contains(5000))

    def test_add_era_rejects_reversed_closed_bounds(self):
        with self.assertRaises(ValueError):
            self.builder.add_era("Invalid", 10, 9)

    def test_builder_round_trip_preserves_era_objects(self):
        self.builder.add_era("BCE", None, -1)
        calendar = self.builder.build()

        rebuilt = CalendarBuilder.from_calendar(calendar).build()

        self.assertEqual(rebuilt.eras, {"BCE": Era(None, -1)})

    def test_add_season(self):
        season = Season(
            "spring",
            "Spring",
            ("mar",),
        )

        self.builder.add_season(season)

        calendar = self.builder.build()

        self.assertEqual(
            calendar.seasons,
            (season,),
        )

    def test_set_weekdays(self):
        weekdays = (
            "Monday",
            "Tuesday",
            "Wednesday",
        )

        self.builder.set_weekdays(weekdays)

        calendar = self.builder.build()

        self.assertEqual(
            calendar.weekdays,
            weekdays,
        )

    def test_set_leap_rule(self):
        rule = LeapRule(
            divisor=4,
            remainder=0,
            exception_divisor=100,
            month_id="feb",
        )

        self.builder.set_leap_rule(rule)

        calendar = self.builder.build()

        self.assertEqual(
            calendar.leap_rule,
            rule,
        )

    def test_build_creates_independent_calendar(self):
        january = Month(
            "jan",
            "January",
            31,
        )

        self.builder.add_month(january)

        first = self.builder.build()

        self.builder.add_month(
            Month("feb", "February", 28)
        )

        second = self.builder.build()

        self.assertEqual(first.month_count, 1)
        self.assertEqual(second.month_count, 2)

    def test_build_does_not_share_month_collection(self):
        self.builder.add_month(
            Month("jan", "January", 31)
        )

        first = self.builder.build()

        self.builder.add_month(
            Month("feb", "February", 28)
        )

        self.assertEqual(
            first.month_count,
            1,
        )
        
    def test_build_does_not_share_mutable_builder_state(self):
        self.builder.add_month(
            Month("jan", "January", 31)
        )

        first = self.builder.build()

        self.builder.add_month(
            Month("feb", "February", 28)
        )

        self.assertEqual(
            first.month_count,
            1,
        )

