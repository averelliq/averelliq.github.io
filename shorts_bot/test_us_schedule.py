"""Credential-free checks for US publishing slots and timezone conversion."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from us_window import publication_slot


class USShortsScheduleTests(unittest.TestCase):
    def test_summer_three_distinct_eastern_and_pacific_slots(self):
        expected = (
            (datetime(2026, 9, 18, 20, 15, tzinfo=timezone.utc), 'science', '16:15 EDT', '13:15 PDT'),
            (datetime(2026, 9, 18, 23, 15, tzinfo=timezone.utc), 'history', '19:15 EDT', '16:15 PDT'),
            (datetime(2026, 9, 19, 2, 15, tzinfo=timezone.utc), 'everyday', '22:15 EDT', '19:15 PDT'),
        )
        for instant, theme, east, west in expected:
            with self.subTest(slot=theme):
                due, found_theme, label = publication_slot(instant)
                self.assertTrue(due)
                self.assertEqual(theme, found_theme)
                self.assertIn(east, label)
                self.assertIn(west, label)

    def test_winter_three_distinct_eastern_and_pacific_slots(self):
        expected = (
            (datetime(2027, 1, 15, 21, 15, tzinfo=timezone.utc), 'science', '16:15 EST', '13:15 PST'),
            (datetime(2027, 1, 16, 0, 15, tzinfo=timezone.utc), 'history', '19:15 EST', '16:15 PST'),
            (datetime(2027, 1, 16, 3, 15, tzinfo=timezone.utc), 'everyday', '22:15 EST', '19:15 PST'),
        )
        for instant, theme, east, west in expected:
            with self.subTest(slot=theme):
                due, found_theme, label = publication_slot(instant)
                self.assertTrue(due)
                self.assertEqual(theme, found_theme)
                self.assertIn(east, label)
                self.assertIn(west, label)

    def test_unused_utc_candidate_is_skipped_in_each_season(self):
        for instant in (
            datetime(2026, 9, 18, 21, 15, tzinfo=timezone.utc),
            datetime(2027, 1, 15, 20, 15, tzinfo=timezone.utc),
            datetime(2027, 1, 16, 2, 15, tzinfo=timezone.utc),
        ):
            self.assertEqual(publication_slot(instant)[0:2], (False, ''))

    def test_naive_datetime_is_rejected(self):
        with self.assertRaises(ValueError):
            publication_slot(datetime(2026, 9, 18, 20, 15))


if __name__ == '__main__':
    unittest.main()
