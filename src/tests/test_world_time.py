import unittest

from src.common.calendar import (
    Calendar,
    CalendarEpoch,
    CalendarManager,
    DayLength,
    Month,
    WorldClock,
    WorldTime,
    WorldTimeDelta,
)


class TestWorldTime(unittest.TestCase):
    def setUp(self):
        calendar = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Monday",),
            seasons=(),
            months=(
                Month("jan", "January", 31),
                Month("feb", "February", 28),
            ),
            eras={},
            epoch=CalendarEpoch(
                datetime=__import__("datetime").datetime(
                    2026,
                    1,
                    1,
                ),
            ),
            leap_rule=None,
        )

        WorldClock.configure(
            CalendarManager(calendar),
            WorldTime(
                2026,
                0,
                0,
                0,
                0,
                0,
            ),
        )

    def test_now_returns_world_time(self):
        result = WorldTime.now()

        self.assertIsInstance(
            result,
            WorldTime,
        )

    def test_negative_years_advance_across_calendar_epoch(self):
        result = WorldTime(
            0,
            0,
            0,
            0,
            0,
            0,
        ).advance(WorldTimeDelta(days=-1))

        self.assertEqual(result.year, -1)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 27)

    def test_now_returns_current_clock_state(self):
        expected = WorldTime(
            2026,
            0,
            0,
            0,
            0,
            0,
        )

        self.assertEqual(
            WorldTime.now(),
            expected,
        )

    def test_world_time_can_be_compared(self):
        first = WorldTime(
            2026,
            0,
            0,
            0,
            0,
            0,
        )

        second = WorldTime(
            2026,
            0,
            1,
            0,
            0,
            0,
        )

        self.assertLess(first, second)
        self.assertLessEqual(first, second)
        self.assertGreater(second, first)
        self.assertGreaterEqual(second, first)

    def test_world_time_subtraction_returns_timedelta(self):
        first = WorldTime(
            2026,
            0,
            1,
            0,
            0,
            0,
        )

        second = WorldTime(
            2026,
            0,
            0,
            0,
            0,
            0,
        )

        result = first - second

        self.assertIsInstance(
            result,
            WorldTimeDelta,
        )

        self.assertEqual(
            result.total_seconds(),
            86400,
        )

    def test_world_time_can_be_advanced(self):
        world_time = WorldTime(
            2026,
            0,
            0,
            0,
            0,
            0,
        )

        result = world_time + WorldTimeDelta(days=1)

        self.assertEqual(
            result,
            WorldTime(
                2026,
                0,
                1,
                0,
                0,
                0,
            ),
        )

    def test_advance_preserves_world_time_type(self):
        world_time = WorldTime.now()

        result = world_time + WorldTimeDelta(seconds=1)

        self.assertIsInstance(
            result,
            WorldTime,
        )
        
    def test_advance_across_day_boundary(self):
        world_time = WorldTime(
            2026,
            0,
            0,
            23,
            30,
            0,
        )

        result = world_time + WorldTimeDelta(hours=2)

        self.assertEqual(
            result,
            WorldTime(
                2026,
                0,
                1,
                1,
                30,
                0,
            ),
        )

    def test_advance_across_month_boundary(self):
        world_time = WorldTime(
            2026,
            0,
            30,
            23,
            30,
            0,
        )

        result = world_time + WorldTimeDelta(hours=2)

        self.assertEqual(
            result,
            WorldTime(
                2026,
                1,
                0,
                1,
                30,
                0,
            ),
        )

    def test_advance_across_year_boundary(self):
        world_time = WorldTime(
            2026,
            1,
            27,
            23,
            30,
            0,
        )

        result = world_time + WorldTimeDelta(hours=2)

        self.assertEqual(
            result,
            WorldTime(
                2027,
                0,
                0,
                1,
                30,
                0,
            ),
        )

    def test_advance_backwards_across_day_boundary(self):
        world_time = WorldTime(
            2026,
            0,
            1,
            0,
            30,
            0,
        )

        result = world_time + WorldTimeDelta(hours=-2)

        self.assertEqual(
            result,
            WorldTime(
                2026,
                0,
                0,
                22,
                30,
                0,
            ),
        )

    def test_advance_backwards_across_month_boundary(self):
        world_time = WorldTime(
            2026,
            1,
            0,
            0,
            30,
            0,
        )

        result = world_time + WorldTimeDelta(hours=-2)

        self.assertEqual(
            result,
            WorldTime(
                2026,
                0,
                30,
                22,
                30,
                0,
            ),
        )

    def test_advance_multiple_days(self):
        world_time = WorldTime(
            2026,
            0,
            0,
            12,
            0,
            0,
        )

        result = world_time + WorldTimeDelta(days=35)

        self.assertEqual(
            result,
            WorldTime(
                2026,
                1,
                4,
                12,
                0,
                0,
            ),
        )
