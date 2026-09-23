import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.database import Database
from app.main_window import MainWindow

APP = QApplication.instance() or QApplication([])


def _make_window(directory):
    settings_path = Path(directory) / "settings.ini"
    settings_factory = lambda *_: QSettings(
        str(settings_path), QSettings.Format.IniFormat
    )
    patches = (
        patch("app.main_window.Database", lambda: Database(directory)),
        patch("app.settings.QSettings", settings_factory),
    )
    for entered in patches:
        entered.__enter__()
    try:
        return MainWindow()
    finally:
        for entered in patches:
            entered.__exit__(None, None, None)


def _close(window):
    window.database.close()
    window.close()


class ShellNavigationTests(unittest.TestCase):
    def test_sidebar_switches_pages_and_preserves_timer(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.task_input.setText("Keep me")
            window.toggle_timer()
            self.assertTrue(window.timer.is_running())

            window.navigate("history")
            self.assertEqual(window.pages.currentIndex(), 1)
            self.assertEqual(window.sidebar.current(), "history")
            self.assertTrue(window.timer.is_running())
            self.assertEqual(window.engine.current_task, "Keep me")

            window.navigate("stats")
            window.navigate("goals")
            self.assertEqual(window.pages.currentIndex(), 3)
            window.navigate("focus")
            self.assertEqual(window.pages.currentIndex(), 0)
            self.assertTrue(window.timer.is_running())
            _close(window)

    def test_unknown_page_falls_back_to_focus(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.navigate("nope")
            self.assertEqual(window.pages.currentIndex(), 0)
            _close(window)


class CompletionBannerTests(unittest.TestCase):
    def test_break_prompt_is_non_blocking_and_starts_break(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.settings.set_notifications_enabled(False)
            window.task_input.setText("Cycle task")
            window.start_timer()
            window.timer.reset(1)
            window.timer._on_tick()
            self.assertEqual(window.mode, "Short Break")
            self.assertTrue(window.focus_view.is_completion_active())
            self.assertIn(
                "Short Break", window.focus_view.banner_action.text()
            )
            window.focus_view.banner_action.click()
            self.assertFalse(window.focus_view.is_completion_active())
            self.assertTrue(window.timer.is_running())
            self.assertEqual(window.mode, "Short Break")
            _close(window)

    def test_later_dismisses_without_starting(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.settings.set_notifications_enabled(False)
            window.current_task = "Review code"
            window.timer.reset(1)
            window.show_break_dialog = lambda _b: window.focus_view.show_completion(
                "t", "m", "Go", lambda: None
            )
            window.timer._on_tick()
            self.assertEqual(window.mode, "Short Break")
            self.assertFalse(window.timer.is_running())
            window.focus_view.hide_completion()
            self.assertFalse(window.focus_view.is_completion_active())
            _close(window)

    def test_finished_focus_shows_banner_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.settings.set_notifications_enabled(False)
            window.task_input.setText("Banner task")
            window.start_timer()
            window.timer.reset(1)
            window.timer._on_tick()
            self.assertEqual(window.mode, "Short Break")
            self.assertTrue(window.focus_view.is_completion_active())
            saved = window.database.connection.execute(
                "SELECT task FROM sessions"
            ).fetchone()
            self.assertEqual(saved, ("Banner task",))
            _close(window)

    def test_empty_task_shows_inline_prompt_not_modal(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.start_timer()
            self.assertFalse(window.timer.is_running())
            self.assertTrue(window.focus_view.is_completion_active())
            _close(window)


class SettingsBehaviorTests(unittest.TestCase):
    def test_save_without_changes_keeps_paused_timer(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.task_input.setText("Paused work")
            window.start_timer()
            window.pause_timer()
            remaining = window.timer.remaining_seconds

            dialog = _FakeAcceptedDialog(window)
            window._apply_saved_settings(dialog)
            self.assertFalse(window.timer.is_running())
            self.assertEqual(window.timer.remaining_seconds, remaining)
            self.assertEqual(window.engine.current_task, "Paused work")
            _close(window)

    def test_duration_change_rearms_idle_timer(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            dialog = _FakeAcceptedDialog(window, focus_minutes=30)
            window._apply_saved_settings(dialog)
            self.assertEqual(window.timer.remaining_seconds, 30 * 60)
            _close(window)

    def test_running_timer_never_touched_by_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.task_input.setText("Running work")
            window.start_timer()
            dialog = _FakeAcceptedDialog(window, focus_minutes=30)
            window._apply_saved_settings(dialog)
            self.assertTrue(window.timer.is_running())
            self.assertEqual(window.engine.current_task, "Running work")
            _close(window)


class _FakeAcceptedDialog:
    """Stands in for SettingsDialog with pre-set spin values."""

    def __init__(self, window, focus_minutes=None):
        self.window = window
        self.focus_minutes = (
            window.settings.get_focus_minutes()
            if focus_minutes is None
            else focus_minutes
        )

    def save_settings(self):
        self.window.settings.set_focus_minutes(self.focus_minutes)


class HistoryViewTests(unittest.TestCase):
    def _seed(self, database):
        now = datetime.now().isoformat(timespec="seconds")
        database.add_session("Write tests", now, 1500)
        database.add_session("Review code", now, 600)

    def test_renders_rows_and_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            self._seed(window.database)
            view = window.history_view
            window.navigate("history")
            view.refresh()
            self.assertEqual(view.sessions_table.rowCount(), 2)
            view.search_input.setText("write")
            self.assertEqual(view.sessions_table.rowCount(), 1)
            self.assertEqual(
                view.sessions_table.item(0, 1).text(), "Write tests"
            )
            view.search_input.clear()
            _close(window)

    def test_pagination(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            now = datetime.now().isoformat(timespec="seconds")
            for index in range(55):
                window.database.add_session(f"T{index}", now, 60)
            view = window.history_view
            view.refresh()
            self.assertEqual(view.sessions_table.rowCount(), 50)
            self.assertIn("Page 1", view.page_label.text())
            view.next_button.click()
            self.assertIn("Page 2", view.page_label.text())
            self.assertEqual(view.sessions_table.rowCount(), 5)
            view.prev_button.click()
            self.assertIn("Page 1", view.page_label.text())
            _close(window)

    def test_export_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            self._seed(window.database)
            path = str(Path(directory) / "export.csv")
            count = window.history_view.export_to_csv(path)
            self.assertEqual(count, 2)
            content = Path(path).read_text(encoding="utf-8")
            self.assertIn("Write tests", content)
            self.assertIn("start_time,task,duration_seconds", content)
            _close(window)

    def test_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            view = window.history_view
            view.refresh()
            self.assertEqual(view.sessions_table.rowCount(), 1)
            self.assertIn(
                "No sessions",
                view.sessions_table.item(0, 0).text(),
            )
            _close(window)

    def test_launch_with_existing_history_opens_unfiltered(self):
        with tempfile.TemporaryDirectory() as directory:
            seed = Database(directory)
            now = datetime.now().isoformat(timespec="seconds")
            seed.add_session("Write tests", now, 1500)
            seed.add_session("Review code", now, 600)
            seed.close()
            window = _make_window(directory)
            view = window.history_view
            items = [
                view.task_combo.itemText(index)
                for index in range(view.task_combo.count())
            ]
            self.assertEqual(items[0], "All tasks")
            self.assertEqual(
                sorted(items[1:]), ["Review code", "Write tests"]
            )
            self.assertEqual(view._current_task_filter(), "")
            self.assertEqual(view.sessions_table.rowCount(), 2)
            view.refresh()
            self.assertEqual(view.sessions_table.rowCount(), 2)
            self.assertEqual(view.task_combo.count(), 3)
            _close(window)


class HistoryFilterPopupThemeTests(unittest.TestCase):
    """Dark-mode regression: the History filter dropdowns must be themed.

    The "All time" / "All tasks" popup lists previously kept Qt's
    system light background while inheriting the theme's light text,
    which made them unreadable in Dark mode.
    """

    def _seed(self, database):
        now = datetime.now().isoformat(timespec="seconds")
        database.add_session("Write tests", now, 1500)
        database.add_session("Review code", now, 600)

    def _row_background_luma(self, combo, row=1):
        """Luma of an unselected popup row background (0 dark … 255 light)."""
        view = combo.view()
        image = view.grab().toImage()
        row_height = image.height() / max(1, view.model().rowCount())
        # Right edge of the row: always background, never the item text.
        color = image.pixelColor(
            image.width() - 2,
            int(row_height * (row + 0.5)),
        )
        return 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()

    def _popup_row_lumas(self, window):
        lumas = []
        for combo in (window.history_view.range_combo,
                      window.history_view.task_combo):
            combo.showPopup()
            APP.processEvents()
            lumas.append(self._row_background_luma(combo))
            combo.hidePopup()
            APP.processEvents()
        return lumas

    def test_dark_mode_popups_use_dark_background(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            self._seed(window.database)
            window.settings.set_theme("Midnight")
            window.apply_theme()
            window.navigate("history")
            window.show()
            APP.processEvents()
            self.assertIn("QComboBox QAbstractItemView", window.styleSheet())
            for luma in self._popup_row_lumas(window):
                self.assertLess(luma, 64)
            _close(window)

    def test_light_mode_popups_keep_system_light_background(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            self._seed(window.database)
            window.settings.set_theme("Minimal")
            window.apply_theme()
            window.navigate("history")
            window.show()
            APP.processEvents()
            # Light mode must not be restyled by the Dark-mode fix.
            self.assertNotIn("QComboBox QAbstractItemView", window.styleSheet())
            for luma in self._popup_row_lumas(window):
                self.assertGreater(luma, 200)
            _close(window)


class GoalsStatsViewTests(unittest.TestCase):
    def test_goals_view_saves_through_service(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            view = window.goals_view
            view.goal_spin.setValue(90)
            view.save_button.click()
            self.assertEqual(
                window.goal_service.get_daily_goal_minutes(), 90
            )
            self.assertIn("90 min", view.status_label.text())
            _close(window)

    def test_stats_view_renders(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            now = datetime.now().isoformat(timespec="seconds")
            window.database.add_session("Write tests", now, 1500)
            window.navigate("stats")
            view = window.stats_view
            view.refresh()
            self.assertIn("25m", view.cards.values["Total"].text())
            self.assertEqual(len(view.chart._data), 14)
            _close(window)

    def test_long_task_name_does_not_break_views(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            now = datetime.now().isoformat(timespec="seconds")
            window.database.add_session("x" * 300, now, 600)
            window.navigate("history")
            window.history_view.refresh()
            window.navigate("stats")
            window.stats_view.refresh()
            window.navigate("goals")
            window.goals_view.refresh()
            _close(window)

    def test_theme_applies_to_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            window.settings.set_theme("Forest")
            window.settings.set_accent_color("#123456")
            window.apply_theme()
            self.assertIn("#sideBar", window.styleSheet())
            self.assertIn("#123456", window.styleSheet())
            _close(window)


if __name__ == "__main__":
    unittest.main()
