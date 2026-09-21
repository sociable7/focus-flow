import sqlite3
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.database import Database, DatabaseError
from app.goals import (
    DEFAULT_DAILY_GOAL_MINUTES,
    GoalManager,
    clamp_goal_minutes,
)
from app.persistence.migrations import (
    CURRENT_VERSION,
    ensure_current,
    get_schema_version,
)
from app.services.goal_service import GoalService
from app.services.settings_store import SettingsStore

APP = QApplication.instance() or QApplication([])


def _make_store(directory):
    path = str(Path(directory) / "settings.ini")
    factory = lambda *_: QSettings(path, QSettings.Format.IniFormat)
    with patch("app.services.settings_store.QSettings", factory):
        return SettingsStore()


def _make_v1_database_file(directory):
    """Create a raw v1-style database file (no daily_goals, version 1)."""
    db_path = Path(directory) / "focus_flow.db"
    connection = sqlite3.connect(db_path)
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
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (
                strftime('%Y-%m-%dT%H:%M:%S', 'now')
            )
        )
        """
    )
    connection.execute(
        "INSERT INTO schema_version (version) VALUES (1)"
    )
    connection.commit()
    return connection


class ClampTests(unittest.TestCase):
    def test_valid_passthrough(self):
        self.assertEqual(clamp_goal_minutes(90), 90)

    def test_clamps_to_range(self):
        self.assertEqual(clamp_goal_minutes(5), 15)
        self.assertEqual(clamp_goal_minutes(9999), 1440)

    def test_junk_recovers_to_default(self):
        self.assertEqual(
            clamp_goal_minutes("junk"), DEFAULT_DAILY_GOAL_MINUTES
        )
        self.assertEqual(clamp_goal_minutes(None), 120)


class MigrationV2Tests(unittest.TestCase):
    def test_fresh_database_is_v2_with_goals_table_and_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            self.assertTrue(database.is_available)
            self.assertEqual(database.get_schema_version(), CURRENT_VERSION)
            self.assertEqual(CURRENT_VERSION, 3)
            tables = {
                row[0]
                for row in database.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertIn("daily_goals", tables)
            indexes = {
                row[0]
                for row in database.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                ).fetchall()
            }
            self.assertIn("idx_sessions_start_time", indexes)
            self.assertIn("idx_sessions_task", indexes)
            self.assertIn(
                "idx_sessions_completed_type_time", indexes
            )
            database.close()

    def test_v1_database_migrates_goals_and_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = _make_v1_database_file(directory)
            raw.execute(
                "INSERT INTO goals (goal_type, target_minutes, date)"
                " VALUES ('daily', 90, '2026-09-20')"
            )
            raw.execute(
                "INSERT INTO goals (goal_type, target_minutes, date)"
                " VALUES ('daily', 60, '2026-09-21')"
            )
            raw.execute(
                "INSERT INTO goals (goal_type, target_minutes, date)"
                " VALUES ('daily', 100, '2026-09-21')"
            )
            raw.execute(
                "INSERT INTO sessions (task, start_time, duration_seconds,"
                " session_type, completed)"
                " VALUES ('Task', '2026-09-20T12:00:00', 1500, 'focus', 1)"
            )
            raw.commit()
            raw.close()

            database = Database(directory)
            self.assertTrue(database.is_available)
            self.assertEqual(database.get_schema_version(), CURRENT_VERSION)
            goals = GoalManager(database)
            # Duplicate legacy rows keep the largest target per date.
            self.assertEqual(goals.get_daily_goal("2026-09-20"), 90)
            self.assertEqual(goals.get_daily_goal("2026-09-21"), 100)
            row = database.connection.execute(
                "SELECT task FROM sessions"
            ).fetchone()
            self.assertEqual(row, ("Task",))
            # Idempotent: second ensure pass changes nothing.
            self.assertTrue(ensure_current(database))
            self.assertEqual(database.get_schema_version(), CURRENT_VERSION)
            self.assertEqual(goals.get_daily_goal("2026-09-21"), 100)
            database.close()

    def test_legacy_database_without_version_table_reaches_v2(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            database.connection.execute("DROP TABLE schema_version")
            database.connection.commit()
            self.assertEqual(
                get_schema_version(database.connection), 0
            )
            self.assertTrue(ensure_current(database))
            self.assertEqual(database.get_schema_version(), CURRENT_VERSION)
            database.close()


class GoalManagerTests(unittest.TestCase):
    def test_default_when_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            self.assertEqual(
                GoalManager(database).get_daily_goal(), 120
            )
            database.close()

    def test_set_and_get_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            goals = GoalManager(database)
            self.assertEqual(goals.set_daily_goal(90), 90)
            self.assertEqual(goals.get_daily_goal(), 90)
            # Second open sees the same row.
            database.close()
            database2 = Database(directory)
            self.assertEqual(
                GoalManager(database2).get_daily_goal(), 90
            )
            database2.close()

    def test_set_clamps_and_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            goals = GoalManager(database)
            self.assertEqual(goals.set_daily_goal(5), 15)
            self.assertEqual(goals.get_daily_goal(), 15)
            self.assertEqual(goals.set_daily_goal(9999), 1440)
            self.assertEqual(goals.set_daily_goal("junk"), 120)
            database.close()

    def test_goals_are_per_day(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            goals = GoalManager(database)
            goals.set_daily_goal(90, "2026-09-20")
            goals.set_daily_goal(60, "2026-09-21")
            self.assertEqual(goals.get_daily_goal("2026-09-20"), 90)
            self.assertEqual(goals.get_daily_goal("2026-09-21"), 60)
            database.close()

    def test_recent_goals_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            goals = GoalManager(database)
            goals.set_daily_goal(90, "2026-09-20")
            goals.set_daily_goal(60, "2026-09-21")
            recent = goals.get_recent_goals(10)
            self.assertEqual(
                recent, [("2026-09-21", 60), ("2026-09-20", 90)]
            )
            self.assertEqual(
                goals.get_recent_goals(1), [("2026-09-21", 60)]
            )
            database.close()

    def test_unavailable_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            database.close()
            goals = GoalManager(database)
            self.assertEqual(goals.get_daily_goal(), 120)
            self.assertEqual(goals.get_recent_goals(), [])
            with self.assertRaises(DatabaseError):
                goals.set_daily_goal(90)


class GoalServiceTests(unittest.TestCase):
    def test_read_prefers_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            service = GoalService(GoalManager(database), store)
            service.set_daily_goal_minutes(90)
            self.assertEqual(service.get_daily_goal_minutes(), 90)
            database.close()

    def test_write_updates_mirror_and_emits(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            service = GoalService(GoalManager(database), store)
            seen = []
            service.valueChanged.connect(seen.append)
            service.set_daily_goal_minutes(90)
            self.assertIn("daily_goal_minutes", seen)
            self.assertEqual(store.get_daily_goal_minutes(), 90)
            database.close()

    def test_falls_back_to_mirror_when_database_down(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            store.set_daily_goal_minutes(75)
            database.close()
            service = GoalService(GoalManager(database), store)
            self.assertEqual(service.get_daily_goal_minutes(), 75)

    def test_import_from_settings_migrates_once(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            store.set_daily_goal_minutes(95)
            service = GoalService(GoalManager(database), store)
            self.assertTrue(service.import_from_settings())
            self.assertEqual(service.get_daily_goal_minutes(), 95)
            # Second import is a no-op (row now exists).
            self.assertFalse(service.import_from_settings())
            database.close()

    def test_import_skips_default_mirror(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            service = GoalService(GoalManager(database), store)
            self.assertFalse(service.import_from_settings())
            database.close()

    def test_import_never_overwrites_database_row(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            service = GoalService(GoalManager(database), store)
            service.set_daily_goal_minutes(80)
            store.set_daily_goal_minutes(95)
            self.assertFalse(service.import_from_settings())
            self.assertEqual(service.get_daily_goal_minutes(), 80)
            database.close()


class GoalUITests(unittest.TestCase):
    def test_settings_dialog_reads_and_writes_through_service(self):
        from app.settings_dialog import SettingsDialog

        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            store = _make_store(directory)
            service = GoalService(GoalManager(database), store)
            service.set_daily_goal_minutes(90)

            dialog = SettingsDialog(
                store, None, None, goal_service=service
            )
            self.assertEqual(dialog.goal_spin.value(), 90)
            dialog.goal_spin.setValue(60)
            dialog.save_settings()
            self.assertEqual(service.get_daily_goal_minutes(), 60)
            self.assertEqual(store.get_daily_goal_minutes(), 60)
            dialog.close()
            database.close()

    def test_settings_dialog_without_service_uses_settings(self):
        from app.settings_dialog import SettingsDialog

        with tempfile.TemporaryDirectory() as directory:
            store = _make_store(directory)
            store.set_daily_goal_minutes(70)
            dialog = SettingsDialog(store, None, None)
            self.assertEqual(dialog.goal_spin.value(), 70)
            dialog.goal_spin.setValue(65)
            dialog.save_settings()
            self.assertEqual(store.get_daily_goal_minutes(), 65)
            dialog.close()

    def test_main_window_goal_display_reflects_database(self):
        from app.main_window import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            settings_factory = lambda *_: QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            with (
                patch(
                    "app.main_window.Database",
                    lambda: Database(directory),
                ),
                patch("app.settings.QSettings", settings_factory),
            ):
                window = MainWindow()
            window.goal_service.set_daily_goal_minutes(120)
            today = datetime.now().isoformat(timespec="seconds")
            window.database.add_session("Task", today, 3600)
            window.update_goal_display()
            self.assertIn("60 / 120 min", window.goal_label.text())
            window.database.close()
            window.close()


if __name__ == "__main__":
    unittest.main()
