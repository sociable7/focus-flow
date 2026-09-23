import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.core.clock import Clock
from app.core.enums import BreakKind, SessionPhase
from app.core.session_engine import SessionEngine
from app.database import Database
from app.persistence.migrations import (
    CURRENT_VERSION,
    ensure_current,
    get_schema_version,
)
from app.services import theme_service
from app.services.settings_store import SettingsStore
from app.timer import PomodoroTimer


APP = QApplication.instance() or QApplication([])


class _FakeSettings:
    """Minimal settings stub for engine tests (no QSettings I/O)."""

    def __init__(self, focus=25, short=5, long=15, cycle=4):
        self._focus = focus
        self._short = short
        self._long = long
        self._cycle = cycle

    def get_focus_minutes(self):
        return self._focus

    def get_short_break_minutes(self):
        return self._short

    def get_long_break_minutes(self):
        return self._long

    def get_sessions_before_long_break(self):
        return self._cycle


class ClockTests(unittest.TestCase):
    def test_pomodoro_timer_is_a_clock(self):
        self.assertTrue(issubclass(PomodoroTimer, Clock))

    def test_completed_clock_is_inert_and_singleshot(self):
        clock = Clock()
        finished = []
        clock.finished.connect(lambda: finished.append(True))
        clock.reset(1)
        clock._on_tick()

        self.assertEqual(clock.remaining_seconds, 0)
        self.assertFalse(clock.is_running())
        self.assertEqual(finished, [True])

        clock._on_tick()
        self.assertEqual(finished, [True])

        clock.start()
        self.assertFalse(clock.is_running())

    def test_pause_preserves_remaining(self):
        clock = Clock()
        clock.reset(60)
        clock.start()
        self.assertTrue(clock.is_running())
        clock.pause()
        self.assertFalse(clock.is_running())
        self.assertEqual(clock.remaining_seconds, 60)


class EngineTests(unittest.TestCase):
    def _engine(self, **kwargs):
        return SessionEngine(Clock(), _FakeSettings(**kwargs))

    def test_initial_state_is_paused_focus(self):
        engine = self._engine()
        engine.load_initial()
        self.assertEqual(engine.phase, SessionPhase.FOCUS)
        self.assertEqual(engine.mode, "Focus")
        self.assertEqual(engine.session_number, 1)
        self.assertEqual(engine.remaining_seconds, 25 * 60)
        self.assertFalse(engine.is_running())

    def test_task_capture_rejects_blank(self):
        engine = self._engine()
        engine.load_initial()
        self.assertFalse(engine.capture_task("   "))
        self.assertEqual(engine.current_task, "")
        self.assertTrue(engine.capture_task("  Write docs  "))
        self.assertEqual(engine.current_task, "Write docs")
        self.assertIsNotNone(engine.focus_start_time)

    def test_focus_finish_prepares_short_break_paused(self):
        engine = self._engine()
        engine.load_initial()
        engine.capture_task("Task")
        engine.start()
        result = engine.finish_current_phase()
        self.assertEqual(result.completed, SessionPhase.FOCUS)
        self.assertEqual(result.task, "Task")
        self.assertEqual(result.duration_seconds, 25 * 60)
        self.assertEqual(result.next_break, BreakKind.SHORT)
        self.assertEqual(engine.phase, SessionPhase.SHORT_BREAK)
        self.assertEqual(engine.remaining_seconds, 5 * 60)
        self.assertFalse(engine.is_running())
        self.assertEqual(engine.current_task, "")

    def test_long_break_at_cycle_end_and_wrap(self):
        engine = self._engine(cycle=2)
        engine.load_initial()
        engine.capture_task("A")
        result = engine.finish_current_phase()
        self.assertEqual(result.next_break, BreakKind.SHORT)
        engine.finish_current_phase()  # short break -> focus 2
        self.assertEqual(engine.session_number, 2)
        engine.capture_task("B")
        result = engine.finish_current_phase()
        self.assertEqual(result.next_break, BreakKind.LONG)
        self.assertEqual(engine.phase, SessionPhase.LONG_BREAK)
        self.assertEqual(engine.remaining_seconds, 15 * 60)
        engine.finish_current_phase()  # long break -> focus wraps to 1
        self.assertEqual(engine.phase, SessionPhase.FOCUS)
        self.assertEqual(engine.session_number, 1)
        self.assertFalse(engine.is_running())

    def test_reset_keeps_phase_and_clears_task(self):
        engine = self._engine()
        engine.load_initial()
        engine.capture_task("Task")
        engine.start()
        engine.reset_phase()
        self.assertEqual(engine.phase, SessionPhase.FOCUS)
        self.assertEqual(engine.current_task, "")
        self.assertEqual(engine.remaining_seconds, 25 * 60)
        self.assertFalse(engine.is_running())

    def test_state_changed_fires(self):
        engine = self._engine()
        seen = []
        engine.stateChanged.connect(lambda: seen.append(True))
        engine.load_initial()
        self.assertTrue(seen)


class SettingsStoreTests(unittest.TestCase):
    def _store(self, directory):
        path = str(Path(directory) / "settings.ini")
        factory = lambda *_: QSettings(
            path, QSettings.Format.IniFormat
        )
        with patch("app.services.settings_store.QSettings", factory):
            return SettingsStore()

    def test_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            self.assertEqual(store.get_focus_minutes(), 25)
            self.assertEqual(store.get_short_break_minutes(), 5)
            self.assertEqual(store.get_long_break_minutes(), 15)
            self.assertEqual(
                store.get_sessions_before_long_break(), 4
            )
            self.assertEqual(store.get_theme(), "Midnight")
            self.assertEqual(store.get_sound(), "System Bell")
            self.assertTrue(store.get_notifications_enabled())
            self.assertEqual(store.get_daily_goal_minutes(), 120)

    def test_validation_clamps_and_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            store.set_focus_minutes(999)
            self.assertEqual(store.get_focus_minutes(), 180)
            store.set_focus_minutes("junk")
            self.assertEqual(store.get_focus_minutes(), 25)
            store.set_theme("Nope")
            self.assertEqual(store.get_theme(), "Midnight")
            store.set_sound("Nope")
            self.assertEqual(store.get_sound(), "System Bell")
            store.set_daily_goal_minutes(5)
            self.assertEqual(store.get_daily_goal_minutes(), 15)

    def test_value_changed_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            seen = []
            store.valueChanged.connect(seen.append)
            store.set_focus_minutes(30)
            self.assertIn("focus_minutes", seen)

    def test_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            store.set_focus_minutes(30)
            store.set_theme("Forest")
            store2 = self._store(directory)
            self.assertEqual(store2.get_focus_minutes(), 30)
            self.assertEqual(store2.get_theme(), "Forest")


class MigrationTests(unittest.TestCase):
    def test_fresh_database_stamped_current(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            self.assertTrue(database.is_available)
            self.assertEqual(
                database.get_schema_version(), CURRENT_VERSION
            )
            database.close()

    def test_ensure_current_idempotent_and_preserves_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            database.add_session("Task", "2026-09-20T12:00:00", 1500)
            self.assertTrue(ensure_current(database))
            self.assertTrue(ensure_current(database))
            self.assertEqual(
                database.get_schema_version(), CURRENT_VERSION
            )
            row = database.connection.execute(
                "SELECT task FROM sessions"
            ).fetchone()
            self.assertEqual(row, ("Task",))
            database.close()

    def test_legacy_database_without_version_table_gets_stamped(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(directory)
            database.connection.execute("DROP TABLE schema_version")
            database.connection.commit()
            self.assertEqual(get_schema_version(database.connection), 0)
            self.assertTrue(ensure_current(database))
            self.assertEqual(
                database.get_schema_version(), CURRENT_VERSION
            )
            database.close()


class ThemeServiceTests(unittest.TestCase):
    @staticmethod
    def _luma(color):
        """Perceptual luma of a ``#RRGGBB`` colour (0 … 255)."""
        return (
            0.299 * int(color[1:3], 16)
            + 0.587 * int(color[3:5], 16)
            + 0.114 * int(color[5:7], 16)
        )

    def test_resolve_defaults_to_midnight(self):
        resolved = theme_service.resolve("Nope", "", "")
        self.assertEqual(resolved["name"], "Midnight")
        self.assertEqual(
            resolved["tokens"]["background"], "#101114"
        )
        self.assertEqual(resolved["accent"], "#8B5CF6")

    def test_resolve_honors_overrides(self):
        resolved = theme_service.resolve(
            "Forest", "#123456", "#654321"
        )
        self.assertEqual(resolved["accent"], "#123456")
        self.assertEqual(resolved["background"], "#654321")
        self.assertEqual(
            resolved["tokens"]["background"], "#F3F7F4"
        )

    def test_stylesheets_embed_tokens(self):
        resolved = theme_service.resolve("Forest", "#123456", "")
        main = theme_service.build_main_window_stylesheet(resolved)
        floating = theme_service.build_floating_stylesheet(resolved)
        self.assertIn("#123456", main)
        self.assertIn("#123456", floating)
        self.assertIn("background: #FFFFFF", floating)

    def test_tonal_variant_shifts_a_subtle_step(self):
        # Dark surfaces lighten, light surfaces darken.
        lighter = theme_service.tonal_variant("#191B20", 1)
        self.assertGreater(self._luma(lighter), self._luma("#191B20"))
        darker = theme_service.tonal_variant("#FFFFFF", 1)
        self.assertLess(self._luma(darker), self._luma("#FFFFFF"))
        # Two steps sit farther from the source than one.
        two = theme_service.tonal_variant("#FFFFFF", 2)
        self.assertLess(self._luma(two), self._luma(darker))
        # Unknown input passes through unchanged; never raises.
        self.assertEqual(theme_service.tonal_variant("nope", 1), "nope")

    def test_ring_palette_is_a_subtle_derivation_per_theme(self):
        from app.themes import THEMES

        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                surface = tokens["surface"]
                track, arc = theme_service.ring_palette(surface)
                source = self._luma(surface)
                one = self._luma(track)
                two = self._luma(arc)
                # Both tones are small tonal steps from the surface...
                self.assertNotEqual(one, source)
                self.assertNotEqual(two, one)
                self.assertLess(abs(one - source), 30)
                self.assertLess(abs(two - source), 60)
                # ...in the same direction, the arc one step farther...
                self.assertEqual(one > source, two > source)
                self.assertGreater(abs(two - source), abs(one - source))
                # ...and never the accent colour.
                self.assertNotEqual(arc, tokens["accent"].lower())
        # Themes with different surfaces derive different palettes.
        self.assertNotEqual(
            theme_service.ring_palette(THEMES["Midnight"]["surface"]),
            theme_service.ring_palette(THEMES["Minimal"]["surface"]),
        )


if __name__ == "__main__":
    unittest.main()
