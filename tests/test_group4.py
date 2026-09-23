"""Group 4 tests: async services, tray/native menus, mini redesign,
System theme, opacity, streak visualization, packaging metadata."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from app import __version__
from app.database import Database
from app.floating_timer import FloatingTimer
from app.main_window import MainWindow
from app.menu_bar import MenuBarManager
from app.native_menu import NativeMenuBar
from app.notifications import NotificationManager
from app.services import theme_service
from app.services.notification_service import NotificationService
from app.services.settings_store import SettingsStore
from app.services.sound_service import SoundService
from app.sounds import SoundManager
from app.timer import PomodoroTimer
from app.ui.components import StreakStrip

APP = QApplication.instance() or QApplication([])


def _temp_store(directory):
    return SettingsStore(
        QSettings(
            str(Path(directory) / "settings.ini"),
            QSettings.Format.IniFormat,
        )
    )


def _drain(ms=100):
    QTest.qWait(ms)


class FakeSoundManager:
    def __init__(self):
        self.calls = []

    def play(self, sound_name, custom_sound=""):
        self.calls.append((sound_name, custom_sound))
        return True


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def show(self, title, message):
        self.calls.append((title, message))


class SoundServiceTests(unittest.TestCase):
    def test_completion_dispatches_without_blocking(self):
        manager = FakeSoundManager()
        with tempfile.TemporaryDirectory() as directory:
            store = _temp_store(directory)
            service = SoundService(manager, store)
            service.play_completion()
            # Dispatched, not synchronous.
            self.assertEqual(manager.calls, [])
            _drain()
            self.assertEqual(len(manager.calls), 1)
            self.assertEqual(manager.calls[0][0], "System Bell")

    def test_preview_is_synchronous_and_never_raises(self):
        manager = FakeSoundManager()
        service = SoundService(manager, None)
        self.assertTrue(service.preview("Double Bell"))

        class Broken:
            def play(self, *args):
                raise RuntimeError("no audio")

        self.assertFalse(SoundService(Broken(), None).preview("X"))
        broken_completion = SoundService(Broken(), None)
        broken_completion.play_completion()  # no settings -> no-op


class NotificationServiceTests(unittest.TestCase):
    def test_disabled_drops_without_delivery(self):
        service = NotificationService(FakeNotifier())
        self.addCleanup(service.shutdown)
        service.set_enabled(False)
        self.assertFalse(service.is_enabled())
        self.assertFalse(service.post("T", "M"))
        self.assertFalse(service.focus_complete())
        _drain()
        self.assertEqual(service.manager.calls, [])

    def test_enabled_delivers_off_thread(self):
        notifier = FakeNotifier()
        service = NotificationService(notifier)
        self.addCleanup(service.shutdown)
        service.set_enabled(True)
        self.assertTrue(service.short_break_complete())
        for _ in range(100):
            if notifier.calls:
                break
            _drain(20)
        self.assertEqual(
            notifier.calls, [("Break finished", "Ready to focus again?")]
        )

    def test_shutdown_is_idempotent(self):
        service = NotificationService(FakeNotifier())
        service.shutdown()
        service.shutdown()
        self.assertFalse(service.post("T", "M"))


class NotificationScriptTests(unittest.TestCase):
    """The osascript command must compile: a single -e argument with
    literal newlines fails (-2741), so the script stays on one line."""

    def _script(self, manager):
        with patch("app.notifications.subprocess.run") as run:
            manager.show("Focus session complete", 'Time for "a" break.')
            argv = run.call_args[0][0]
        self.assertEqual(argv[:2], ["osascript", "-e"])
        self.assertFalse(run.call_args[1].get("check", False))
        return argv[2]

    def test_script_is_single_line(self):
        script = self._script(NotificationManager())
        self.assertNotIn("\n", script)
        self.assertIn('display notification "Focus session complete"', script)
        self.assertIn('with title "Focus Flow"', script)
        # Quotes are escaped so the AppleScript string stays intact.
        self.assertIn('subtitle "Time for \\"a\\" break."', script)

    def test_convenience_methods_use_single_line_scripts(self):
        manager = NotificationManager()
        with patch("app.notifications.subprocess.run") as run:
            manager.focus_complete()
            manager.short_break_complete()
            manager.long_break_complete()
        self.assertEqual(run.call_count, 3)
        for call in run.call_args_list:
            self.assertNotIn("\n", call[0][0][2])

    def test_osascript_failure_never_raises(self):
        manager = NotificationManager()
        with patch(
            "app.notifications.subprocess.run",
            side_effect=OSError("no osascript"),
        ):
            manager.show("T", "M")
            manager.focus_complete()


class ThemeAndOpacityTests(unittest.TestCase):
    def test_system_theme_resolves_to_concrete_palette(self):
        resolved = theme_service.resolve("System", "", "")
        self.assertEqual(resolved["name"], "System")
        self.assertIn("background", resolved["tokens"])
        self.assertTrue(resolved["accent"])
        self.assertIn(
            resolved["tokens"],
            (
                theme_service.resolve("Minimal")["tokens"],
                theme_service.resolve("Midnight")["tokens"],
            ),
        )

    def test_unknown_theme_still_falls_back(self):
        resolved = theme_service.resolve("Nope", "", "")
        self.assertEqual(resolved["name"], "Midnight")

    def test_opacity_round_trip_and_clamping(self):
        with tempfile.TemporaryDirectory() as directory:
            store = _temp_store(directory)
            self.assertEqual(store.get_mini_opacity(), 1.0)
            store.set_mini_opacity(0.75)
            self.assertAlmostEqual(store.get_mini_opacity(), 0.75)
            store.set_mini_opacity(5)
            self.assertEqual(store.get_mini_opacity(), 1.0)
            store.set_mini_opacity(0)
            self.assertEqual(store.get_mini_opacity(), 0.4)
            store.set_mini_opacity("junk")
            self.assertEqual(store.get_mini_opacity(), 0.4)

    def test_system_theme_valid_in_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = _temp_store(directory)
            store.set_theme("System")
            self.assertEqual(store.get_theme(), "System")
            store.set_theme("Nope")
            self.assertEqual(store.get_theme(), "Midnight")


class TrayAndNativeMenuTests(unittest.TestCase):
    def _stub_window(self):
        window = QWidget()
        window.toggle_timer = lambda: None
        window.reset_timer = lambda: None
        window.show = lambda: None
        window.show_floating_timer = lambda: None
        window.close_application = lambda: None
        return window

    def test_tray_sync_updates_tooltip_and_label(self):
        window = self._stub_window()
        tray = MenuBarManager(window)
        tray.sync_state("Focus", "24:59", True)
        self.assertIn("Focus", tray.tray.toolTip())
        self.assertIn("24:59", tray.tray.toolTip())
        self.assertEqual(tray.start_action.text(), "Pause")
        tray.sync_state("Focus", "25:00", False)
        self.assertEqual(tray.start_action.text(), "Start")
        window.close()

    def test_native_menu_builds_and_syncs(self):
        calls = []

        class StubMainWindow(QMainWindow):
            def toggle_timer(self):
                calls.append("toggle")

            def reset_timer(self):
                pass

            def skip_break(self):
                pass

            def navigate(self, page):
                calls.append(page)

            def open_settings(self):
                pass

            def show_about(self):
                pass

            def close_application(self):
                pass

            def toggle_floating_timer(self):
                pass

        window = StubMainWindow()
        menu = NativeMenuBar(window)
        names = [action.text() for action in window.menuBar().actions()]
        self.assertIn("Focus Flow", names)
        self.assertIn("Timer", names)
        self.assertIn("View", names)
        self.assertIn("Window", names)

        menu.sync_state(running=True, is_break=True)
        self.assertEqual(menu.toggle_action.text(), "Pause")
        self.assertTrue(menu.skip_action.isEnabled())
        menu.sync_state(running=False, is_break=False)
        self.assertEqual(menu.toggle_action.text(), "Start")
        self.assertFalse(menu.skip_action.isEnabled())
        window.close()


class MiniRedesignTests(unittest.TestCase):
    def test_progress_skip_and_opacity(self):
        timer = PomodoroTimer()
        timer.reset(1500)
        mini = FloatingTimer(timer, settings=None)
        self.assertFalse(mini.skip_button.isVisibleTo(mini))
        # The ring mirrors elapsed/total from the shared clock (the
        # Clock updates remaining_seconds before every tick).
        timer.remaining_seconds = 750
        mini.update_time(750)
        self.assertAlmostEqual(mini.ring.progress, 0.5)
        mini.set_break_visible(True)
        self.assertTrue(mini.skip_button.isVisibleTo(mini))

        skipped = []
        mini2 = FloatingTimer(
            timer, settings=None, skip_callback=lambda: skipped.append(1)
        )
        mini2.skip_button.click()
        self.assertEqual(skipped, [1])

        mini.apply_opacity()  # no settings -> defaults, never raises
        self.assertEqual(mini.windowOpacity(), 1.0)
        mini.close()

    def test_opacity_applies_from_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            store = _temp_store(directory)
            store.set_mini_opacity(0.6)
            mini = FloatingTimer(PomodoroTimer(), settings=store)
            mini.apply_opacity()
            self.assertAlmostEqual(mini.windowOpacity(), 0.6)
            mini.close()


class StreakVisualizationTests(unittest.TestCase):
    def test_strip_renders_and_describes(self):
        strip = StreakStrip()
        strip.set_colors("#123456", "#000000", "#FFFFFF")
        days = [(f"2026-09-{day:02d}", 600 if day % 2 else 0) for day in range(10, 17)]
        strip.set_data(days, streak=3)
        self.assertEqual(len(strip._days), 7)
        self.assertIn("3 days", strip.accessibleDescription())
        strip.set_data([], streak=0)
        self.assertIn("0 of 0", strip.accessibleDescription())

    def test_stats_view_feeds_strip(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            now = datetime.now().isoformat(timespec="seconds")
            database.add_session("Write tests", now, 1500)
            settings_path = Path(directory) / "settings.ini"
            factory = lambda *_: QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            with (
                patch("app.main_window.Database", lambda: Database(directory)),
                patch("app.settings.QSettings", factory),
            ):
                window = MainWindow()
            window.navigate("stats")
            strip = window.stats_view.streak_strip
            self.assertEqual(len(strip._days), 7)
            self.assertEqual(strip._streak, 1)
            window.database.close()
            window.close()


class ShellIntegrationTests(unittest.TestCase):
    def test_window_wires_group4_services(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            factory = lambda *_: QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            with (
                patch("app.main_window.Database", lambda: Database(directory)),
                patch("app.settings.QSettings", factory),
            ):
                window = MainWindow()
            self.assertIsInstance(window.sound_service, SoundService)
            self.assertIsInstance(window.notification_service, NotificationService)
            self.assertIsInstance(window.native_menu, NativeMenuBar)
            # Engine untouched: sync manager still drives sounds/notifications.
            self.assertIsInstance(window.sound_manager, SoundManager)
            self.assertIs(
                window.notification_service.manager, window.notifications
            )
            window.toggle_floating_timer()
            self.assertTrue(window.floating_timer.isVisible())
            window.toggle_floating_timer()
            self.assertFalse(window.floating_timer.isVisible())
            window.show_about = lambda: None
            window.database.close()
            window.close()

    def test_version_is_published(self):
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
