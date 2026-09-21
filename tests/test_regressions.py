import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from app.database import Database
from app.history import HistoryManager
from app.history_dialog import HistoryDialog
from app.main_window import MainWindow
from app.shortcuts import ShortcutManager
from app.sounds import SoundManager
from app.timer import PomodoroTimer


APP = QApplication.instance() or QApplication([])


class TimerRegressionTests(unittest.TestCase):
    def test_completed_timer_does_not_restart_without_a_reset(self):
        timer = PomodoroTimer()
        completed = []
        timer.finished.connect(lambda: completed.append(True))
        timer.reset(1)
        timer._on_tick()

        self.assertEqual(timer.remaining_seconds, 0)
        self.assertFalse(timer.is_running())
        self.assertEqual(completed, [True])

        timer._on_tick()
        self.assertEqual(completed, [True])

        timer.start()
        self.assertFalse(timer.is_running())

        timer.reset(60)
        timer.start()
        self.assertTrue(timer.is_running())
        timer.pause()

    def test_mode_transitions_reset_the_next_timer_without_starting_focus(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            settings_factory = lambda *_: QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            with (
                patch("app.main_window.Database", lambda: Database(directory)),
                patch("app.settings.QSettings", settings_factory),
            ):
                window = MainWindow()

            window.settings.set_focus_minutes(25)
            window.settings.set_short_break_minutes(5)
            window.settings.set_sessions_before_long_break(4)
            window.session_number = 1

            window.prepare_break("short")
            self.assertEqual(window.mode, "Short Break")
            self.assertEqual(window.timer.remaining_seconds, 5 * 60)
            self.assertFalse(window.timer.is_running())

            window.start_focus()
            self.assertEqual(window.mode, "Focus")
            self.assertEqual(window.session_number, 2)
            self.assertEqual(window.timer.remaining_seconds, 25 * 60)
            self.assertFalse(window.timer.is_running())
            self.assertTrue(window.task_input.isEnabled())

            window.database.close()
            window.close()

    def test_finished_focus_and_break_prepare_the_next_session(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            settings_factory = lambda *_: QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            with (
                patch("app.main_window.Database", lambda: Database(directory)),
                patch("app.settings.QSettings", settings_factory),
            ):
                window = MainWindow()

            window.settings.set_short_break_minutes(5)
            window.settings.set_focus_minutes(25)
            window.settings.set_notifications_enabled(False)
            window.show_break_dialog = lambda _break_type: None
            window.show_focus_dialog = lambda: None
            window.current_task = "Review code"
            window.timer.reset(1)
            window.timer._on_tick()

            self.assertEqual(window.mode, "Short Break")
            self.assertEqual(window.timer.remaining_seconds, 5 * 60)
            self.assertFalse(window.timer.is_running())
            saved = window.database.connection.execute(
                "SELECT task FROM sessions"
            ).fetchone()
            self.assertEqual(saved, ("Review code",))

            window.timer.reset(1)
            window.timer._on_tick()

            self.assertEqual(window.mode, "Focus")
            self.assertEqual(window.timer.remaining_seconds, 25 * 60)
            self.assertFalse(window.timer.is_running())
            self.assertTrue(window.task_input.isEnabled())
            window.database.close()
            window.close()

    def test_floating_timer_is_top_level_and_controls_the_shared_timer(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            settings_factory = lambda *_: QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            with (
                patch("app.main_window.Database", lambda: Database(directory)),
                patch("app.settings.QSettings", settings_factory),
            ):
                window = MainWindow()

            floating = window.floating_timer
            window.show()
            self.assertIs(floating.timer, window.timer)
            self.assertIsNone(floating.parentWidget())
            self.assertTrue(
                floating.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
            )
            self.assertTrue(floating.windowFlags() & Qt.WindowType.Tool)
            self.assertTrue(
                floating.testAttribute(
                    Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow
                )
            )
            self.assertTrue(
                floating.testAttribute(
                    Qt.WidgetAttribute.WA_ShowWithoutActivating
                )
            )

            window.show_floating_timer()
            self.assertTrue(floating.isVisible())
            window.set_mode("Short Break")
            self.assertEqual(floating.mode_label.text(), "SHORT BREAK")
            window.timer.reset(123)
            self.assertEqual(floating.time_label.text(), "02:03")

            window.settings.set_theme("Forest")
            window.settings.set_accent_color("#123456")
            window.apply_theme()
            self.assertIn("background: #FFFFFF", floating.styleSheet())
            self.assertIn("background: #123456", floating.styleSheet())

            window.prepare_focus_session()
            window.task_input.setText("Shared timer task")
            floating.toggle_timer()
            self.assertTrue(window.timer.is_running())
            self.assertEqual(window.current_task, "Shared timer task")
            floating.toggle_timer()
            self.assertFalse(window.timer.is_running())

            window.hide_floating_timer()
            self.assertFalse(floating.isVisible())
            self.assertTrue(window.isVisible())
            window.database.close()
            window.close()


class ShortcutRegressionTests(unittest.TestCase):
    def test_text_entry_does_not_trigger_timer_shortcuts(self):
        window = QWidget()
        task_input = QLineEdit(window)
        calls = {"toggle": 0, "reset": 0}
        window.toggle_timer = lambda: calls.__setitem__("toggle", calls["toggle"] + 1)
        window.reset_timer = lambda: calls.__setitem__("reset", calls["reset"] + 1)
        manager = ShortcutManager(window)

        window.show()
        task_input.setFocus()
        QTest.keyClicks(task_input, "write a report")
        APP.processEvents()

        self.assertEqual(task_input.text(), "write a report")
        self.assertEqual(calls, {"toggle": 0, "reset": 0})
        self.assertEqual(len(manager.start_pause), 2)
        self.assertEqual(len(manager.reset), 2)
        window.close()


class SoundRegressionTests(unittest.TestCase):
    def test_all_sound_options_resolve_to_a_persistent_effect(self):
        manager = SoundManager()
        sound = manager.system_bell_sound

        self.assertTrue(sound.is_file())
        self.assertTrue(manager.play("System Bell"))
        self.assertTrue(manager.play("Double Bell"))
        self.assertTrue(manager.play("Custom WAV", str(sound)))
        self.assertIn(sound.resolve(), manager._effects)


class DatabaseRegressionTests(unittest.TestCase):
    def test_database_creates_and_writes_in_application_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            self.assertTrue(database.is_available, database.error_message)

            database.add_session("Write tests", "2026-09-20T12:00:00", 1500)
            row = database.connection.execute(
                "SELECT task, duration_seconds FROM sessions"
            ).fetchone()

            self.assertEqual(row, ("Write tests", 1500))
            database.close()


class HistoryDisplayTests(unittest.TestCase):
    def test_history_dialog_shows_completed_sessions_only(self):
        class Settings:
            def get_theme(self):
                return "Midnight"

            def get_background_color(self):
                return ""

            def get_accent_color(self):
                return ""

        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            now = datetime.now().isoformat(timespec="seconds")
            database.add_session("Completed task", now, 1500)
            database.add_session(
                "Cancelled task",
                now,
                600,
                completed=False,
            )
            history = HistoryManager(database)

            self.assertEqual(history.get_all(), [("Completed task", now, 1500)])

            dialog = HistoryDialog(history, Settings())
            self.assertEqual(dialog.sessions_table.rowCount(), 1)
            self.assertEqual(
                dialog.sessions_table.item(0, 1).text(), "Completed task"
            )
            self.assertEqual(dialog.sessions_table.item(0, 2).text(), "25m")
            self.assertIn("25m", dialog.total_value.text())
            dialog.close()
            database.close()


if __name__ == "__main__":
    unittest.main()
