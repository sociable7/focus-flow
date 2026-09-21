import tempfile
import unittest
from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication

from app.database import Database
from app.history import HistoryManager
from app.history_dialog import HistoryDialog

APP = QApplication.instance() or QApplication([])


def _stamp(days_ago=0, hour=12, minute=0):
    moment = datetime.now().replace(
        hour=hour, minute=minute, second=0, microsecond=0
    ) - timedelta(days=days_ago)
    return moment.isoformat(timespec="seconds")


def _seed(database):
    database.add_session("Write tests", _stamp(0), 1500)
    database.add_session("Write tests", _stamp(1), 1500)
    database.add_session("Review code", _stamp(1), 600)
    database.add_session("Write tests", _stamp(2), 3000)
    database.add_session(
        "Cancelled task", _stamp(0), 600, completed=False
    )


class HistoryTotalsTests(unittest.TestCase):
    def test_lifetime_total_and_count(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            _seed(database)
            history = HistoryManager(database)
            self.assertEqual(history.get_total(), 1500 + 1500 + 600 + 3000)
            self.assertEqual(history.get_session_count(), 4)
            database.close()

    def test_empty_database_reports_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            self.assertEqual(history.get_total(), 0)
            self.assertEqual(history.get_session_count(), 0)
            self.assertEqual(history.get_day_streak(), 0)
            self.assertEqual(history.get_task_breakdown(), [])
            self.assertEqual(len(history.get_daily_totals(7)), 7)
            database.close()

    def test_incomplete_sessions_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            database.add_session(
                "Cancelled", _stamp(0), 3600, completed=False
            )
            database.add_session(
                "Break", _stamp(0), 300, session_type="break"
            )
            self.assertEqual(history.get_total(), 0)
            self.assertEqual(history.get_session_count(), 0)
            self.assertEqual(history.get_day_streak(), 0)
            database.close()

    def test_unavailable_database_returns_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            database.close()
            self.assertEqual(history.get_total(), 0)
            self.assertEqual(history.get_session_count(), 0)
            self.assertEqual(history.get_day_streak(), 0)
            self.assertEqual(history.get_task_breakdown(), [])
            self.assertEqual(history.get_recent_sessions(), [])
            self.assertEqual(len(history.get_daily_totals(7)), 7)


class DailyTotalsTests(unittest.TestCase):
    def test_seven_days_oldest_first_zero_filled(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            _seed(database)
            history = HistoryManager(database)
            daily = history.get_daily_totals(7)
            self.assertEqual(len(daily), 7)
            self.assertEqual(
                [day for day, _ in daily], sorted(day for day, _ in daily)
            )
            by_day = dict(daily)
            today = datetime.now().date().isoformat()
            yesterday = (
                datetime.now().date() - timedelta(days=1)
            ).isoformat()
            two_ago = (
                datetime.now().date() - timedelta(days=2)
            ).isoformat()
            six_ago = (
                datetime.now().date() - timedelta(days=6)
            ).isoformat()
            self.assertEqual(by_day[today], 1500)
            self.assertEqual(by_day[yesterday], 2100)
            self.assertEqual(by_day[two_ago], 3000)
            self.assertEqual(by_day[six_ago], 0)
            database.close()

    def test_invalid_window_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            self.assertEqual(len(history.get_daily_totals("junk")), 7)
            self.assertEqual(len(history.get_daily_totals(0)), 1)
            database.close()


class StreakTests(unittest.TestCase):
    def test_consecutive_days(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            _seed(database)
            history = HistoryManager(database)
            self.assertEqual(history.get_day_streak(), 3)
            database.close()

    def test_gap_breaks_streak(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            database.add_session("A", _stamp(0), 600)
            database.add_session("B", _stamp(2), 600)
            self.assertEqual(history.get_day_streak(), 1)
            database.close()

    def test_missing_today_keeps_yesterday_streak(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            database.add_session("A", _stamp(1), 600)
            database.add_session("B", _stamp(2), 600)
            self.assertEqual(history.get_day_streak(), 2)
            database.close()


class TaskBreakdownTests(unittest.TestCase):
    def test_ordered_by_total_descending(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            _seed(database)
            history = HistoryManager(database)
            breakdown = history.get_task_breakdown()
            self.assertEqual(
                breakdown,
                [
                    ("Write tests", 6000, 3),
                    ("Review code", 600, 1),
                ],
            )
            database.close()

    def test_limit_and_invalid_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            _seed(database)
            history = HistoryManager(database)
            self.assertEqual(len(history.get_task_breakdown(1)), 1)
            self.assertEqual(
                len(history.get_task_breakdown("junk")), 2
            )
            database.close()


class RecentSessionsTests(unittest.TestCase):
    def test_paged_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            for index in range(60):
                database.add_session(
                    f"Task {index}", _stamp(0, hour=8, minute=0), 600
                )
            history = HistoryManager(database)
            recent = history.get_recent_sessions(50)
            self.assertEqual(len(recent), 50)
            # get_all still returns the full unbounded list.
            self.assertEqual(len(history.get_all()), 60)
            self.assertEqual(len(history.get_recent_sessions("junk")), 50)
            database.close()


class HistoryDialogTests(unittest.TestCase):
    class Settings:
        def get_theme(self):
            return "Midnight"

        def get_background_color(self):
            return ""

        def get_accent_color(self):
            return ""

    def test_dialog_shows_new_analytics(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            _seed(database)
            history = HistoryManager(database)
            dialog = HistoryDialog(history, self.Settings())
            self.assertIn("3 days", dialog.streak_value.text())
            self.assertIn("4 sessions", dialog.sessions_value.text())
            self.assertIn("Write tests", dialog.top_task_value.text())
            self.assertEqual(len(dialog.day_labels), 7)
            strip = " ".join(
                label.text() for label in dialog.day_labels
            )
            self.assertIn("25m", strip)
            # Existing summaries and table are unchanged.
            self.assertIn("25m", dialog.today_value.text())
            self.assertEqual(dialog.sessions_table.rowCount(), 4)
            dialog.close()
            database.close()

    def test_dialog_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            history = HistoryManager(database)
            dialog = HistoryDialog(history, self.Settings())
            self.assertIn("0 days", dialog.streak_value.text())
            self.assertIn("0 sessions", dialog.sessions_value.text())
            self.assertIn("—", dialog.top_task_value.text())
            self.assertEqual(dialog.sessions_table.rowCount(), 1)
            dialog.close()
            database.close()


if __name__ == "__main__":
    unittest.main()
