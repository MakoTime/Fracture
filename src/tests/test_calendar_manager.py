import unittest
from datetime import datetime, timezone

from src.common.calendar.model import (
    Calendar,
    CalendarEpoch,
    DayLength,
    Month,
    Season,
)
from src.common.calendar.manager import CalendarManager


class TestCalendarManager(unittest.TestCase):
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

        self.manager = CalendarManager(self.calendar)

    def test_calendar(self):
        self.assertIs(
            self.manager.calendar,
            self.calendar,
        )

    def test_can_undo_initially_false(self):
        self.assertFalse(self.manager.can_undo)

    def test_can_redo_initially_false(self):
        self.assertFalse(self.manager.can_redo)

    def test_add_month(self):
        month_id = self.manager.add_month(
            "May",
            31,
        )

        self.assertEqual(
            self.manager.calendar.months[-1].id,
            month_id,
        )
        self.assertEqual(
            self.manager.calendar.months[-1].name,
            "May",
        )
        self.assertEqual(
            self.manager.calendar.months[-1].days,
            31,
        )

    def test_add_month_with_index(self):
        month_id = self.manager.add_month(
            "May",
            31,
            1,
        )

        self.assertEqual(
            self.manager.calendar.months[1].id,
            month_id,
        )

    def test_add_month_creates_undo_state(self):
        original = self.manager.calendar

        self.manager.add_month("May", 31)

        self.assertTrue(self.manager.can_undo)
        self.assertIsNot(
            self.manager.calendar,
            original,
        )

    def test_remove_month(self):
        self.manager.remove_month("feb")

        self.assertEqual(
            tuple(month.id for month in self.manager.calendar.months),
            ("jan", "mar", "apr"),
        )

    def test_rename_month(self):
        self.manager.rename_month(
            "jan",
            "First Month",
        )

        self.assertEqual(
            self.manager.calendar.months[0].name,
            "First Month",
        )

    def test_set_month_days(self):
        self.manager.set_month_days(
            "feb",
            29,
        )

        self.assertEqual(
            self.manager.calendar.months[1].days,
            29,
        )

    def test_move_month(self):
        self.manager.move_month(
            "apr",
            0,
        )

        self.assertEqual(
            tuple(month.id for month in self.manager.calendar.months),
            ("apr", "jan", "feb", "mar"),
        )

    def test_add_season(self):
        season_id = self.manager.add_season(
            "Summer",
            ("jan", "feb"),
        )

        season = next(
            season
            for season in self.manager.calendar.seasons
            if season.id == season_id
        )

        self.assertEqual(
            season.name,
            "Summer",
        )
        self.assertEqual(
            season.month_ids,
            ("jan", "feb"),
        )

    def test_remove_season(self):
        self.manager.remove_season("spring")

        self.assertEqual(
            self.manager.calendar.seasons,
            (),
        )

    def test_rename_season(self):
        self.manager.rename_season(
            "spring",
            "Growing Season",
        )

        self.assertEqual(
            self.manager.calendar.seasons[0].name,
            "Growing Season",
        )

    def test_set_season_months(self):
        self.manager.set_season_months(
            "spring",
            ("jan", "feb"),
        )

        self.assertEqual(
            self.manager.calendar.seasons[0].month_ids,
            ("jan", "feb"),
        )

    def test_set_leap_rule(self):
        self.manager.set_leap_rule(
            4,
            0,
            100,
            "feb",
        )

        rule = self.manager.calendar.leap_rule

        self.assertIsNotNone(rule)
        self.assertEqual(rule.divisor, 4)
        self.assertEqual(rule.remainder, 0)
        self.assertEqual(rule.exception_divisor, 100)
        self.assertEqual(rule.month_id, "feb")

    def test_remove_leap_rule(self):
        self.manager.set_leap_rule(
            4,
            0,
            100,
            "feb",
        )

        self.manager.remove_leap_rule()

        self.assertIsNone(
            self.manager.calendar.leap_rule,
        )

    def test_undo(self):
        original = self.manager.calendar

        self.manager.add_month("May", 31)

        restored = self.manager.undo()

        self.assertIs(
            restored,
            original,
        )
        self.assertIs(
            self.manager.calendar,
            original,
        )
        self.assertFalse(self.manager.can_undo)
        self.assertTrue(self.manager.can_redo)

    def test_redo(self):
        self.manager.add_month("May", 31)
        edited = self.manager.calendar

        self.manager.undo()
        restored = self.manager.redo()

        self.assertIs(
            restored,
            edited,
        )
        self.assertIs(
            self.manager.calendar,
            edited,
        )
        self.assertTrue(self.manager.can_undo)
        self.assertFalse(self.manager.can_redo)

    def test_undo_without_history_returns_current_calendar(self):
        current = self.manager.calendar

        result = self.manager.undo()

        self.assertIs(
            result,
            current,
        )

    def test_redo_without_history_returns_current_calendar(self):
        current = self.manager.calendar

        result = self.manager.redo()

        self.assertIs(
            result,
            current,
        )

    def test_new_edit_clears_redo_history(self):
        self.manager.add_month("May", 31)
        self.manager.undo()

        self.assertTrue(self.manager.can_redo)

        self.manager.add_month("June", 30)

        self.assertFalse(self.manager.can_redo)

    def test_replace(self):
        replacement = Calendar(
            day_length=DayLength(24, 0, 0),
            weekdays=("Day 1",),
            seasons=(),
            months=(
                Month("x", "Example", 10),
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

        self.manager.replace(replacement)

        self.assertIs(
            self.manager.calendar,
            replacement,
        )
        self.assertFalse(self.manager.can_undo)
        self.assertFalse(self.manager.can_redo)

    def test_edit_does_not_modify_previous_calendar(self):
        original = self.manager.calendar

        self.manager.rename_month(
            "jan",
            "First Month",
        )

        self.assertEqual(
            original.months[0].name,
            "January",
        )
        self.assertEqual(
            self.manager.calendar.months[0].name,
            "First Month",
        )

    def test_multiple_edits_can_be_undone_in_order(self):
        original = self.manager.calendar

        self.manager.rename_month("jan", "First")
        first_edit = self.manager.calendar

        self.manager.rename_month("feb", "Second")
        second_edit = self.manager.calendar

        self.assertIs(
            self.manager.undo(),
            first_edit,
        )
        self.assertIs(
            self.manager.undo(),
            original,
        )

        self.assertIs(
            self.manager.redo(),
            first_edit,
        )
        self.assertIs(
            self.manager.redo(),
            second_edit,
        )


if __name__ == "__main__":
    unittest.main()
