"""Focused regression tests for mini-window interaction wiring.

Covers the bug where any mini-window click activated the main window:
pause/start, skip-break, close, and background drag must all work
without showing or activating the main window, against the SAME shared
timer instance.

Also covers the focus -> break -> next-focus state transitions through
the mini controls (SessionEngine stays the source of truth), the
explicit "Open Main Window" action, and the task-gate behavior that
previously made mini Start look dead after Skip Break.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.database import Database
from app.main_window import MainWindow

APP = QApplication.instance() or QApplication([])


def _make_window(directory):
    settings_path = Path(directory) / "settings.ini"
    factory = lambda *_: QSettings(
        str(settings_path), QSettings.Format.IniFormat
    )
    with (
        patch("app.main_window.Database", lambda: Database(directory)),
        patch("app.settings.QSettings", factory),
    ):
        window = MainWindow()
    return window


def _mouse_event(etype, local, glob, button, buttons):
    return QMouseEvent(
        etype,
        QPointF(local),
        QPointF(glob),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


class MiniInteractionTests(unittest.TestCase):
    def test_mini_shares_the_same_timer_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                window.show()
                self.assertIs(window.floating_timer.timer, window.timer)
                self.assertIsNone(window.floating_timer.parentWidget())
            finally:
                window.database.close()
                window.close()

    def test_mini_is_non_activating(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                self.assertTrue(
                    floating.windowFlags()
                    & Qt.WindowType.WindowDoesNotAcceptFocus
                )
                self.assertEqual(
                    floating.focusPolicy(), Qt.FocusPolicy.NoFocus
                )
                for button in (
                    floating.pause_button,
                    floating.skip_button,
                    floating.close_button,
                ):
                    self.assertEqual(
                        button.focusPolicy(), Qt.FocusPolicy.NoFocus
                    )
            finally:
                window.database.close()
                window.close()

    def test_pause_start_does_not_show_or_move_main_window(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.prepare_focus_session()
                window.task_input.setText("Shared timer task")
                # Simulate "inactive app": main hidden, mini shown alone.
                window.hide()
                window.show_floating_timer()
                self.assertTrue(floating.isVisible())

                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())

                floating.pause_button.click()
                self.assertFalse(window.timer.is_running())
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())
            finally:
                window.database.close()
                window.close()

    def test_skip_break_does_not_show_main_window(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                from app.core.enums import SessionPhase

                floating = window.floating_timer
                window.show()
                window.prepare_break("short")
                self.assertEqual(window.engine.phase, SessionPhase.SHORT_BREAK)
                window.hide()
                window.show_floating_timer()
                floating.set_break_visible(True)
                self.assertTrue(floating.isVisible())

                floating.skip_button.click()
                self.assertEqual(window.engine.phase, SessionPhase.FOCUS)
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())
            finally:
                window.database.close()
                window.close()

    def test_close_hides_mini_only_and_keeps_timer_state(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.prepare_focus_session()
                window.task_input.setText("Keep running")
                window.hide()
                window.show_floating_timer()
                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())

                floating.close_button.click()
                self.assertFalse(floating.isVisible())
                # Main window untouched, timer still running, app alive.
                self.assertFalse(window.isVisible())
                self.assertTrue(window.timer.is_running())
                self.assertIsNotNone(QApplication.instance())
            finally:
                window.database.close()
                window.close()

    def test_background_press_drags_but_button_press_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.show_floating_timer()
                start = floating.pos()

                label = floating.time_label
                local = label.rect().center()
                glob = label.mapToGlobal(local)

                press = _mouse_event(
                    QEvent.Type.MouseButtonPress,
                    local,
                    glob,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                )
                QApplication.sendEvent(label, press)
                self.assertTrue(floating._dragging)

                moved = glob + QPointF(40, 30).toPoint()
                move = _mouse_event(
                    QEvent.Type.MouseMove,
                    local + QPointF(40, 30).toPoint(),
                    moved,
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.LeftButton,
                )
                QApplication.sendEvent(label, move)
                self.assertEqual(
                    (floating.pos() - start).manhattanLength(), 70
                )

                release = _mouse_event(
                    QEvent.Type.MouseButtonRelease,
                    local,
                    moved,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.NoButton,
                )
                QApplication.sendEvent(label, release)
                self.assertFalse(floating._dragging)
                # Position persisted for the next launch.
                self.assertEqual(
                    window.settings.get_mini_position(),
                    (floating.pos().x(), floating.pos().y()),
                )

                # Presses on buttons must not start a drag.
                button = floating.pause_button
                bloc = button.rect().center()
                bglob = button.mapToGlobal(bloc)
                bpress = _mouse_event(
                    QEvent.Type.MouseButtonPress,
                    bloc,
                    bglob,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                )
                QApplication.sendEvent(button, bpress)
                self.assertFalse(floating._dragging)
            finally:
                window.database.close()
                window.close()

    def test_activation_from_mini_keeps_mini(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.hide()
                window.show_floating_timer()
                self.assertTrue(floating.isVisible())

                with patch.object(
                    QApplication,
                    "activeWindow",
                    staticmethod(lambda: floating),
                ):
                    window._on_app_activated()
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())

                with patch.object(
                    QApplication,
                    "activeWindow",
                    staticmethod(lambda: window),
                ):
                    window._on_app_activated()
                self.assertFalse(floating.isVisible())
                self.assertTrue(window.isVisible())
            finally:
                window.database.close()
                window.close()

    def test_activation_from_mini_click_without_focus_keeps_mini(self):
        """macOS case: mini never becomes activeWindow (NoFocus by design).

        Simulates a mini click that activated the *application* while the
        mini itself stayed non-active: activeWindow() is None and
        isActiveWindow() is False, but the pointer is over the mini. The
        handler must keep the mini and keep the main window hidden so the
        pending button/drag click is not preempted.
        """
        from PySide6.QtGui import QCursor

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.hide()
                window.show_floating_timer()
                self.assertTrue(floating.isVisible())
                center = floating.frameGeometry().center()
                with (
                    patch.object(
                        QApplication,
                        "activeWindow",
                        staticmethod(lambda: None),
                    ),
                    patch.object(
                        type(floating),
                        "isActiveWindow",
                        lambda self: False,
                    ),
                    patch.object(QCursor, "pos", staticmethod(lambda: center)),
                    patch.object(
                        QApplication,
                        "widgetAt",
                        staticmethod(lambda pos: floating),
                    ),
                ):
                    window._on_app_activated()
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())
                # The pending button click must still work afterwards.
                window.prepare_focus_session()
                window.task_input.setText("Still shared")
                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())
            finally:
                window.database.close()
                window.close()

    def test_activation_elsewhere_restores_main(self):
        """Genuine return (Dock/Cmd-Tab): pointer away -> hide mini."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QCursor

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.hide()
                window.show_floating_timer()
                self.assertTrue(floating.isVisible())
                far = QPoint(-10000, -10000)
                with (
                    patch.object(
                        QApplication,
                        "activeWindow",
                        staticmethod(lambda: None),
                    ),
                    patch.object(
                        type(floating),
                        "isActiveWindow",
                        lambda self: False,
                    ),
                    patch.object(QCursor, "pos", staticmethod(lambda: far)),
                    patch.object(
                        QApplication, "widgetAt", staticmethod(lambda pos: None)
                    ),
                ):
                    window._on_app_activated()
                self.assertFalse(floating.isVisible())
                self.assertTrue(window.isVisible())
            finally:
                window.database.close()
                window.close()

    def test_deactivation_hides_main_and_shows_mini(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                self.assertTrue(window.isVisible())
                window._on_app_deactivated()
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())
                # Idempotent: second call neither flickers nor moves.
                pos = floating.pos()
                window._on_app_deactivated()
                self.assertTrue(floating.isVisible())
                self.assertFalse(window.isVisible())
                self.assertEqual(floating.pos(), pos)
            finally:
                window.database.close()
                window.close()


def _start_focus_with_task(window, task):
    """Begin a focus session the way the UI requires (task captured)."""
    window.prepare_focus_session()
    window.task_input.setText(task)
    window.hide()
    window.show_floating_timer()
    window.floating_timer.pause_button.click()  # Start
    assert window.timer.is_running()


def _finish_current_phase(window):
    """Force the running phase to complete (1s + one tick)."""
    window.timer.reset(1)
    window.timer._on_tick()


class MiniStateTransitionTests(unittest.TestCase):
    """Focus -> break -> next-focus flows driven via mini buttons only.

    The SessionEngine is the source of truth throughout: the mini
    never starts the raw timer directly, and starting a focus session
    still requires a captured task (the main window's "Add a focus
    task" gate). The regression that made mini Start look dead after
    Skip Break was that gate firing with feedback visible only on the
    hidden main window; the mini now mirrors the hint and offers an
    explicit path back via "Open Main Window".
    """

    def test_skip_break_then_start_with_task_starts_next_focus(self):
        from app.core.enums import SessionPhase

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.settings.set_focus_minutes(25)
                window.settings.set_short_break_minutes(5)
                window.settings.set_notifications_enabled(False)
                window.show_break_dialog = lambda _b: None
                window.show_focus_dialog = lambda: None
                window.show()

                _start_focus_with_task(window, "First task")
                _finish_current_phase(window)

                # Break prepared, paused, full duration.
                self.assertEqual(
                    window.engine.phase, SessionPhase.SHORT_BREAK
                )
                self.assertFalse(window.timer.is_running())
                self.assertEqual(window.timer.remaining_seconds, 5 * 60)
                self.assertTrue(
                    floating.skip_button.isVisibleTo(floating)
                )
                self.assertEqual(floating.pause_button.text(), "Start")

                # Skip Break from the mini prepares the next focus.
                floating.skip_button.click()
                self.assertEqual(window.engine.phase, SessionPhase.FOCUS)
                self.assertFalse(window.timer.is_running())
                self.assertEqual(window.timer.remaining_seconds, 25 * 60)
                self.assertFalse(
                    floating.skip_button.isVisibleTo(floating)
                )
                self.assertEqual(floating.pause_button.text(), "Start")

                # No mini click opened the main window.
                self.assertFalse(window.isVisible())
                self.assertTrue(floating.isVisible())

                # Next focus needs its own task (unchanged product rule);
                # with one entered, mini Start really starts the timer.
                window.task_input.setText("Second task")
                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())
                self.assertEqual(window.engine.phase, SessionPhase.FOCUS)
                self.assertEqual(
                    window.engine.current_task, "Second task"
                )
                self.assertEqual(floating.pause_button.text(), "Pause")
                self.assertFalse(window.isVisible())
                self.assertTrue(floating.isVisible())

                # Mini and main agree on phase, time and task.
                self.assertEqual(
                    floating.time_label.text(), window.time_label.text()
                )
                self.assertEqual(
                    floating.mode_label.text(), window.mode.upper()
                )
                self.assertEqual(
                    floating.task_label.text(), "Second task"
                )
            finally:
                window.database.close()
                window.close()

    def test_start_break_from_mini_runs_break(self):
        from app.core.enums import SessionPhase

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.settings.set_short_break_minutes(5)
                window.settings.set_notifications_enabled(False)
                window.show_break_dialog = lambda _b: None
                window.show_focus_dialog = lambda: None
                window.show()

                _start_focus_with_task(window, "Break-bound task")
                _finish_current_phase(window)
                self.assertEqual(
                    window.engine.phase, SessionPhase.SHORT_BREAK
                )

                # Breaks need no task: mini Start runs the break.
                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())
                self.assertEqual(
                    window.engine.phase, SessionPhase.SHORT_BREAK
                )
                self.assertEqual(floating.pause_button.text(), "Pause")
                self.assertFalse(window.isVisible())
                self.assertTrue(floating.isVisible())
                self.assertEqual(
                    floating.mode_label.text(), window.mode.upper()
                )
            finally:
                window.database.close()
                window.close()

    def test_break_finish_prepares_focus_and_start_needs_task(self):
        from app.core.enums import SessionPhase

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.settings.set_focus_minutes(25)
                window.settings.set_short_break_minutes(5)
                window.settings.set_notifications_enabled(False)
                window.show_break_dialog = lambda _b: None
                window.show_focus_dialog = lambda: None
                window.show()

                _start_focus_with_task(window, "Cycle task")
                _finish_current_phase(window)
                floating.pause_button.click()  # start the break
                self.assertTrue(window.timer.is_running())
                _finish_current_phase(window)

                # Next focus prepared, paused, full duration.
                self.assertEqual(window.engine.phase, SessionPhase.FOCUS)
                self.assertFalse(window.timer.is_running())
                self.assertEqual(window.timer.remaining_seconds, 25 * 60)
                self.assertFalse(
                    floating.skip_button.isVisibleTo(floating)
                )

                # Mini Start with no task stays paused but is no longer
                # silent: the main banner and the mini hint both say a
                # task is needed, and the main window stays hidden.
                floating.pause_button.click()
                self.assertFalse(window.timer.is_running())
                self.assertTrue(
                    window.focus_view.is_completion_active()
                )
                self.assertEqual(
                    window.focus_view.banner_title.text(),
                    "Add a focus task",
                )
                self.assertTrue(
                    floating.task_label.isVisibleTo(floating)
                )
                self.assertEqual(
                    floating.task_label.text(),
                    "Add a task in the main window",
                )
                self.assertFalse(window.isVisible())
                self.assertTrue(floating.isVisible())

                # With a task entered, mini Start runs the next focus.
                window.task_input.setText("After break")
                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())
                self.assertEqual(
                    window.engine.current_task, "After break"
                )
                self.assertEqual(
                    floating.task_label.text(), "After break"
                )
            finally:
                window.database.close()
                window.close()


class MiniOpenMainWindowTests(unittest.TestCase):
    def test_open_main_window_restores_main_and_hides_mini(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                _start_focus_with_task(window, "Open-path task")
                self.assertFalse(window.isVisible())
                self.assertTrue(floating.isVisible())

                remaining = window.timer.remaining_seconds
                phase = window.engine.phase
                main_id = id(window)

                floating.open_button.click()

                # Same window object, now visible; mini hidden.
                self.assertEqual(id(window), main_id)
                self.assertTrue(window.isVisible())
                self.assertFalse(floating.isVisible())
                # Timer state untouched.
                self.assertTrue(window.timer.is_running())
                self.assertEqual(window.timer.remaining_seconds, remaining)
                self.assertEqual(window.engine.phase, phase)
                self.assertEqual(
                    window.engine.current_task, "Open-path task"
                )
            finally:
                window.database.close()
                window.close()

    def test_open_main_window_restores_from_minimized(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.showMinimized()
                self.assertTrue(window.isMinimized())
                window.show_floating_timer()

                floating.open_button.click()

                self.assertFalse(window.isMinimized())
                self.assertTrue(window.isVisible())
                self.assertFalse(floating.isVisible())
            finally:
                window.database.close()
                window.close()

    def test_open_button_wiring_is_explicit_and_drag_safe(self):
        from PySide6.QtWidgets import QPushButton

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.show_floating_timer()

                button = floating.open_button
                self.assertIsInstance(button, QPushButton)
                self.assertEqual(button.text(), "Open Main Window")
                self.assertEqual(
                    button.focusPolicy(), Qt.FocusPolicy.NoFocus
                )
                self.assertEqual(
                    button.accessibleName(), "Open main window"
                )
                # Routed through MainWindow, like toggle/skip callbacks.
                self.assertEqual(
                    floating.open_callback.__func__,
                    MainWindow.show_main_window_from_mini,
                )
                self.assertIs(
                    floating.open_callback.__self__, window
                )

                # Pressing the button never starts a drag (QPushButtons
                # are excluded from the drag filter).
                local = button.rect().center()
                glob = button.mapToGlobal(local)
                press = _mouse_event(
                    QEvent.Type.MouseButtonPress,
                    local,
                    glob,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                )
                QApplication.sendEvent(button, press)
                self.assertFalse(floating._dragging)

                # Background dragging still works with the new layout.
                start = floating.pos()
                label = floating.time_label
                local = label.rect().center()
                glob = label.mapToGlobal(local)
                press = _mouse_event(
                    QEvent.Type.MouseButtonPress,
                    local,
                    glob,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                )
                QApplication.sendEvent(label, press)
                self.assertTrue(floating._dragging)
                moved = glob + QPointF(40, 30).toPoint()
                move = _mouse_event(
                    QEvent.Type.MouseMove,
                    local + QPointF(40, 30).toPoint(),
                    moved,
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.LeftButton,
                )
                QApplication.sendEvent(label, move)
                self.assertEqual(
                    (floating.pos() - start).manhattanLength(), 70
                )
                release = _mouse_event(
                    QEvent.Type.MouseButtonRelease,
                    local,
                    moved,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.NoButton,
                )
                QApplication.sendEvent(label, release)
                self.assertFalse(floating._dragging)
            finally:
                window.database.close()
                window.close()

    def test_close_mini_does_not_quit_or_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.prepare_focus_session()
                window.task_input.setText("Keep running")
                window.hide()
                window.show_floating_timer()
                floating.pause_button.click()  # start
                floating.pause_button.click()  # pause for exact compare
                self.assertFalse(window.timer.is_running())
                remaining = window.timer.remaining_seconds
                total = window.timer.total_seconds
                phase = window.engine.phase

                floating.close_button.click()

                self.assertFalse(floating.isVisible())
                # Main window untouched, timer untouched, app alive.
                self.assertFalse(window.isVisible())
                self.assertFalse(window.timer.is_running())
                self.assertEqual(window.timer.remaining_seconds, remaining)
                self.assertEqual(window.timer.total_seconds, total)
                self.assertEqual(window.engine.phase, phase)
                self.assertEqual(
                    window.engine.current_task, "Keep running"
                )
                self.assertIsNotNone(QApplication.instance())
            finally:
                window.database.close()
                window.close()


class FloatingRingSyncTests(unittest.TestCase):
    """The ring mirrors the shared Clock; the widget owns no timer state."""

    def test_ring_progress_tracks_the_shared_clock(self):
        from app.floating_timer import FloatingTimer
        from app.timer import PomodoroTimer

        timer = PomodoroTimer()
        timer.reset(1500)
        mini = FloatingTimer(timer, settings=None)
        self.assertAlmostEqual(mini.ring.progress, 0.0)

        # The Clock decrements remaining_seconds, then emits tick.
        timer.remaining_seconds = 750
        timer.tick.emit(750)
        self.assertAlmostEqual(mini.ring.progress, 0.5)

        timer.remaining_seconds = 0
        timer.tick.emit(0)  # completion fills the ring
        self.assertAlmostEqual(mini.ring.progress, 1.0)

        timer.reset(1200)  # next phase (skip/prepare) emits its tick
        self.assertAlmostEqual(mini.ring.progress, 0.0)
        self.assertEqual(mini.time_label.text(), "20:00")
        mini.close()

    def test_ring_glides_between_ticks_without_jumping(self):
        from unittest.mock import patch

        from app.floating_timer import FloatingTimer
        from app.timer import PomodoroTimer

        timer = PomodoroTimer()
        timer.reset(1500)
        mini = FloatingTimer(timer, settings=None)
        clock = {"now": 1000.0}
        with (
            patch.object(timer, "is_running", return_value=True),
            patch(
                "app.ui.progress_ring.time.monotonic",
                side_effect=lambda: clock["now"],
            ),
        ):
            mini.update_time(750)  # tick anchored at t=1000.0
            self.assertAlmostEqual(mini.ring.progress, 0.5)

            clock["now"] = 1000.5  # between whole-second ticks
            mini._sync_ring_progress()
            halfway = mini.ring.progress
            self.assertGreater(halfway, 0.5)
            # Moves smoothly, but never more than the elapsed slice:
            # no once-per-second jumps around the circumference.
            self.assertLess(halfway - 0.5, 1.0 / 1500)

            clock["now"] = 1001.0
            mini._sync_ring_progress()
            self.assertGreater(mini.ring.progress, halfway)

            mini.update_time(749)  # next real tick resyncs exactly
            self.assertAlmostEqual(
                mini.ring.progress, (1500 - 749) / 1500
            )
        mini.close()

    def test_pause_freezes_and_resume_continues_from_same_point(self):
        from unittest.mock import patch

        from app.floating_timer import FloatingTimer
        from app.timer import PomodoroTimer

        timer = PomodoroTimer()
        timer.reset(300)
        timer.remaining_seconds = 120  # paused with 02:00 remaining
        mini = FloatingTimer(timer, settings=None)
        clock = {"now": 5000.0}
        with patch(
            "app.ui.progress_ring.time.monotonic",
            side_effect=lambda: clock["now"],
        ):
            mini.update_time(120)
            frozen = mini.ring.progress
            self.assertAlmostEqual(frozen, (300 - 120) / 300)

            clock["now"] = 9000.0  # wall time passes while paused
            mini._sync_ring_progress()
            self.assertEqual(mini.ring.progress, frozen)

        with (
            patch.object(timer, "is_running", return_value=True),
            patch(
                "app.ui.progress_ring.time.monotonic",
                side_effect=lambda: clock["now"],
            ),
        ):
            mini._sync_ring_progress()  # resume: same point...
            self.assertAlmostEqual(mini.ring.progress, frozen)
            clock["now"] = 9000.5
            mini._sync_ring_progress()  # ...then it keeps moving
            self.assertGreater(mini.ring.progress, frozen)
        mini.close()


class FloatingControlsStabilityTests(unittest.TestCase):
    """Controls stay visible and stable — no hover fade, no surprises.

    Regression guard for the hover/opacity redesign: a control must
    never fade out while it can still receive clicks, hovering must
    not change geometry or hit-testing, and the close button stays at
    the top of the window, separate from the timer controls.
    """

    CONTROLS = ("close_button", "pause_button", "skip_button", "open_button")

    @staticmethod
    def _enter(floating):
        from PySide6.QtGui import QEnterEvent

        floating.enterEvent(
            QEnterEvent(QPointF(0, 0), QPointF(0, 0), QPointF(0, 0))
        )

    @staticmethod
    def _leave(floating):
        floating.leaveEvent(QEvent(QEvent.Type.Leave))

    @staticmethod
    def _snapshot(floating):
        """Geometry, size and programmatic visibility of every control."""
        state = {"size": floating.size()}
        for name in FloatingControlsStabilityTests.CONTROLS:
            button = getattr(floating, name)
            state[name] = (
                button.geometry(),
                button.isVisibleTo(floating),
                button.isEnabled(),
            )
        return state

    @staticmethod
    def _pause_button_pixel(floating):
        """Rendered centre pixel of the pause button in the window."""
        from PySide6.QtCore import QPoint

        image = floating.grab().toImage()
        center = floating.pause_button.geometry().center() + QPoint(
            floating.container.pos().x(), floating.container.pos().y()
        )
        return image.pixelColor(center)

    def test_no_opacity_fade_anywhere_on_the_floating_timer(self):
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.show_floating_timer()
                APP.processEvents()

                # No fade machinery at all: nothing can become
                # visually hidden while still hit-testable.
                self.assertEqual(
                    floating.findChildren(QGraphicsOpacityEffect), []
                )
                self.assertFalse(hasattr(floating, "controls_effect"))
                # At rest the controls are fully visible, not "quiet".
                self.assertTrue(floating.pause_button.isVisibleTo(floating))
                self.assertTrue(floating.open_button.isVisibleTo(floating))
                self.assertTrue(floating.close_button.isVisibleTo(floating))
            finally:
                window.database.close()
                window.close()

    def test_hover_does_not_change_geometry_visibility_or_pixels(self):
        from PySide6.QtTest import QTest

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.show_floating_timer()
                APP.processEvents()

                at_rest = self._snapshot(floating)
                pixel_at_rest = self._pause_button_pixel(floating)
                # Visible control renders opaque accent, not a ghost.
                self.assertGreaterEqual(pixel_at_rest.alpha(), 250)

                self._enter(floating)
                QTest.qWait(250)  # long enough for any fade to finish
                hovered = self._snapshot(floating)
                self.assertEqual(hovered, at_rest)
                self.assertEqual(floating.size(), at_rest["size"])
                self.assertEqual(
                    self._pause_button_pixel(floating), pixel_at_rest
                )

                self._leave(floating)
                QTest.qWait(250)
                self.assertEqual(self._snapshot(floating), at_rest)
                self.assertEqual(
                    self._pause_button_pixel(floating), pixel_at_rest
                )
            finally:
                window.database.close()
                window.close()

    def test_control_stays_clickable_while_hovered(self):
        from PySide6.QtTest import QTest

        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.prepare_focus_session()
                window.task_input.setText("Hover task")
                window.hide()
                window.show_floating_timer()
                APP.processEvents()

                self._enter(floating)
                QTest.qWait(250)
                # Pressed while hovered: visible, opaque, and it works.
                floating.pause_button.click()
                self.assertTrue(window.timer.is_running())
                self.assertTrue(floating.pause_button.isVisibleTo(floating))
                self.assertGreaterEqual(
                    self._pause_button_pixel(floating).alpha(), 250
                )
                floating.pause_button.click()
                self.assertFalse(window.timer.is_running())
            finally:
                window.database.close()
                window.close()

    def test_close_button_stays_at_the_top_of_the_window(self):
        with tempfile.TemporaryDirectory() as directory:
            window = _make_window(directory)
            try:
                floating = window.floating_timer
                window.show()
                window.show_floating_timer()
                APP.processEvents()

                close = floating.close_button
                # All controls share the container's coordinate space.
                self.assertIs(close.parentWidget(), floating.container)
                # Above the ring readout...
                self.assertLess(close.geometry().top(),
                                floating.ring.geometry().top())
                # ...and well above the pause/skip/open control row,
                # i.e. visually and functionally separate from it.
                self.assertLess(close.geometry().bottom(),
                                floating.pause_button.geometry().top())
                self.assertLess(close.geometry().bottom(),
                                floating.open_button.geometry().top())
                # Right-aligned in the top row, 24x24 as before.
                self.assertEqual(close.size(), close.minimumSize())
                self.assertEqual(close.size().height(), 24)

                # Existing close behaviour preserved: hides the mini
                # only; the timer and main window are untouched.
                main_visible = window.isVisible()
                floating.close_button.click()
                self.assertFalse(floating.isVisible())
                self.assertEqual(window.isVisible(), main_visible)
            finally:
                window.database.close()
                window.close()


if __name__ == "__main__":
    unittest.main()
