import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

from app.database import Database
from app.history import HistoryManager
from app.persistence.migrations import CURRENT_VERSION
from app.persistence.session_repo import SessionRepository


def _stamp(days_ago=0, hour=12, minute=0):
    moment = datetime.now().replace(
        hour=hour, minute=minute, second=0, microsecond=0
    ) - timedelta(days=days_ago)
    return moment.isoformat(timespec="seconds")


def _make_v2_database(directory):
    """Fabricate a v2-shaped database (no v3 columns, stamped at v2)."""
    path = f"{directory}/focus_flow.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            session_type TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_type TEXT NOT NULL,
            target_minutes INTEGER NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE daily_goals (
            date TEXT PRIMARY KEY,
            target_minutes INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (
                strftime('%Y-%m-%dT%H:%M:%S', 'now')
            )
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (
                strftime('%Y-%m-%dT%H:%M:%S', 'now')
            )
        )
        """
    )
    connection.execute(
        "INSERT INTO schema_version (version) VALUES (2)"
    )
    connection.execute(
        """
        INSERT INTO sessions (task, start_time, duration_seconds,
                              session_type, completed)
        VALUES (?, ?, ?, 'focus', 1)
        """,
        ("Write Tests", _stamp(0), 1500),
    )
    connection.execute(
        """
        INSERT INTO sessions (task, start_time, duration_seconds,
                              session_type, completed)
        VALUES (?, ?, ?, 'focus', 1)
        """,
        ("write tests", _stamp(1), 600),
    )
    connection.commit()
    connection.close()


class MigrationV3Tests(unittest.TestCase):
    def test_v2_upgrades_to_v3_with_backfill(self):
        with tempfile.TemporaryDirectory() as directory:
            _make_v2_database(directory)
            database = Database(directory)
            self.assertTrue(database.is_available)
            self.assertEqual(
                database.get_schema_version(), CURRENT_VERSION
            )
            self.assertEqual(CURRENT_VERSION, 3)
            columns = {
                row[1]
                for row in database.connection.execute(
                    "PRAGMA table_info(sessions)"
                ).fetchall()
            }
            self.assertIn("end_time", columns)
            self.assertIn("planned_seconds", columns)
            self.assertIn("task_norm", columns)
            rows = database.connection.execute(
                "SELECT task, task_norm, planned_seconds,"
                " duration_seconds FROM sessions"
                " ORDER BY start_time DESC"
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    ("Write Tests", "write tests", 1500, 1500),
                    ("write tests", "write tests", 600, 600),
                ],
            )
            database.close()

    def test_migration_idempotent_and_preserves_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            _make_v2_database(directory)
            first = Database(directory)
            first.close()
            second = Database(directory)
            self.assertEqual(
                second.get_schema_version(), CURRENT_VERSION
            )
            count = second.connection.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            self.assertEqual(count, 2)
            second.close()

    def test_fresh_database_has_v3_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            columns = {
                row[1]
                for row in database.connection.execute(
                    "PRAGMA table_info(sessions)"
                ).fetchall()
            }
            self.assertIn("end_time", columns)
            self.assertIn("planned_seconds", columns)
            self.assertIn("task_norm", columns)
            database.close()


class SessionWriteTests(unittest.TestCase):
    def test_new_fields_persisted_with_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            database.add_session("Write tests", _stamp(0), 1500)
            row = database.connection.execute(
                "SELECT task_norm, planned_seconds, end_time"
                " FROM sessions"
            ).fetchone()
            self.assertEqual(row, ("write tests", 1500, None))
            database.add_session(
                "Review",
                _stamp(0),
                900,
                end_time=_stamp(0, hour=13),
                planned_seconds=1500,
            )
            row = database.connection.execute(
                "SELECT task_norm, planned_seconds, end_time"
                " FROM sessions WHERE task = 'Review'"
            ).fetchone()
            self.assertEqual(
                row, ("review", 1500, _stamp(0, hour=13))
            )
            database.close()


class RepositoryQueryTests(unittest.TestCase):
    def _seeded(self, directory):
        database = Database(directory)
        database.add_session("Write tests", _stamp(0), 1500)
        database.add_session("WRITE TESTS", _stamp(1), 1500)
        database.add_session("Review code", _stamp(1), 600)
        database.add_session(
            "Cancelled", _stamp(0), 600, completed=False
        )
        return database

    def test_totals_ignore_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            database = self._seeded(directory)
            repo = SessionRepository(database)
            self.assertEqual(repo.today_total(), 1500)
            self.assertEqual(repo.week_total(), 1500 + 1500 + 600)
            self.assertEqual(
                repo.lifetime_total(), 1500 + 1500 + 600
            )
            self.assertEqual(repo.session_count(), 3)
            database.close()

    def test_per_task_groups_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            database = self._seeded(directory)
            repo = SessionRepository(database)
            breakdown = repo.per_task()
            self.assertEqual(len(breakdown), 2)
            # Most-recent casing wins for the merged display name.
            self.assertEqual(breakdown[0][1], 3000)
            self.assertEqual(breakdown[0][2], 2)
            self.assertEqual(breakdown[0][0], "Write tests")
            self.assertEqual(
                repo.total_for_task("  write TESTS "), 3000
            )
            database.close()

    def test_page_pagination_search_and_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            for index in range(60):
                database.add_session(
                    f"Task {index}", _stamp(0, hour=8), 600
                )
            database.add_session(
                "Special job", _stamp(2), 600
            )
            repo = SessionRepository(database)
            first = repo.page(limit=50)
            self.assertEqual(len(first), 50)
            rest = repo.page(limit=50, offset=50)
            self.assertEqual(len(rest), 11)
            hits = repo.page(limit=100, task_query="tAsK 1")
            self.assertTrue(hits)
            self.assertTrue(
                all("task 1" in task.lower() for task, _, _ in hits)
            )
            today = datetime.now().date().isoformat()
            two_ago = (
                datetime.now().date() - timedelta(days=2)
            ).isoformat()
            self.assertEqual(
                len(repo.page(limit=100, date_from=today)), 60
            )
            self.assertEqual(
                len(
                    repo.page(
                        limit=100,
                        date_from=two_ago,
                        date_to=two_ago,
                    )
                ),
                1,
            )
            self.assertEqual(repo.page(limit="junk"), repo.page())
            database.close()

    def test_series_zero_filled_and_streak(self):
        with tempfile.TemporaryDirectory() as directory:
            database = self._seeded(directory)
            repo = SessionRepository(database)
            series = repo.daily_series(7)
            self.assertEqual(len(series), 7)
            self.assertEqual(
                [day for day, _ in series],
                sorted(day for day, _ in series),
            )
            by_day = dict(series)
            self.assertEqual(by_day[datetime.now().date().isoformat()], 1500)
            self.assertEqual(repo.day_streak(), 2)
            database.close()

    def test_unavailable_database_returns_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            repo = SessionRepository(database)
            database.close()
            self.assertEqual(repo.today_total(), 0)
            self.assertEqual(repo.lifetime_total(), 0)
            self.assertEqual(repo.session_count(), 0)
            self.assertEqual(repo.per_task(), [])
            self.assertEqual(repo.page(), [])
            self.assertEqual(repo.day_streak(), 0)
            self.assertEqual(len(repo.daily_series(7)), 7)

    def test_facade_matches_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            database = self._seeded(directory)
            repo = SessionRepository(database)
            history = HistoryManager(database)
            self.assertEqual(history.get_all(), repo.get_all())
            self.assertEqual(
                history.get_recent_sessions(2), repo.get_recent(2)
            )
            self.assertEqual(
                history.get_daily_totals(7), repo.daily_series(7)
            )
            self.assertEqual(
                history.get_task_breakdown(), repo.per_task()
            )
            self.assertEqual(history.get_tasks(), repo.tasks())
            database.close()


if __name__ == "__main__":
    unittest.main()
