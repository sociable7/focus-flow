from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from app.core.enums import BreakKind, SessionPhase
from app.core.session_engine import SessionEngine
from app.database import Database, DatabaseError
from app.floating_timer import FloatingTimer
from app.goals import GoalManager
from app.history import HistoryManager
from app.history_dialog import HistoryDialog
from app.menu_bar import MenuBarManager
from app.native_menu import NativeMenuBar
from app.notifications import NotificationManager
from app.services import theme_service
from app.services.goal_service import GoalService
from app.services.notification_service import NotificationService
from app.services.sound_service import SoundService
from app.settings import AppSettings
from app.settings_dialog import SettingsDialog
from app.shortcuts import ShortcutManager
from app.sounds import SoundManager
from app.timer import PomodoroTimer
from app.ui.focus_view import FocusView
from app.ui.goals_view import GoalsView
from app.ui.history_view import HistoryView
from app.ui.sidebar import SideNav
from app.ui.stats_view import StatsView


class MainWindow(QMainWindow):
    """Application shell: sidebar navigation plus wiring.

    Timer state lives in ``SessionEngine``; session data in
    ``SessionRepository`` (via ``HistoryManager``); goals in
    ``GoalService``. This class coordinates those services with the
    views and preserves the public attribute surface used by tests
    and controllers (tray, shortcuts, floating timer).
    """

    def __init__(self):
        super().__init__()

        # =====================================================
        # Core services
        # =====================================================

        self.settings = AppSettings()

        self.timer = PomodoroTimer()

        self.sound_manager = SoundManager(self)

        self.sound_service = SoundService(
            self.sound_manager,
            self.settings,
            self,
        )

        self.database = Database()

        self.history = HistoryManager(
            self.database
        )

        self.goals = GoalManager(
            self.database
        )

        self.goal_service = GoalService(
            self.goals,
            self.settings,
        )

        self.goal_service.import_from_settings()

        self.goal_service.valueChanged.connect(
            self._on_goal_changed
        )

        self.notifications = (
            NotificationManager()
        )

        # Async delivery (Group 4): the manager stays the sync engine
        # (and the compatibility attribute); the service runs it on a
        # worker thread so osascript never blocks the event loop.
        self.notification_service = NotificationService(
            self.notifications,
            self,
        )
        self.notification_service.set_enabled(
            self.settings.get_notifications_enabled()
        )

        # =====================================================
        # Session engine (single source of truth for timer state)
        # =====================================================

        self.engine = SessionEngine(
            self.timer,
            self.settings,
        )

        self.engine.stateChanged.connect(
            self._on_engine_state
        )

        # =====================================================
        # Timer state (mirrors of engine state for compatibility)
        # =====================================================

        self.mode = "Focus"

        self.session_number = 1

        self.current_task = ""

        self.focus_start_time = None

        # =====================================================
        # Window
        # =====================================================

        self.setWindowTitle(
            "Focus Flow"
        )

        self.setMinimumSize(
            740,
            620,
        )

        self.resize(
            900,
            740,
        )

        # =====================================================
        # Build application
        # =====================================================

        self.build_ui()

        self.connect_signals()

        self.load_initial_timer()

        self.apply_theme()

        self.update_buttons()

        self.navigate("focus")

        # =====================================================
        # Additional controllers
        # =====================================================

        self.floating_timer = (
            FloatingTimer(
                self.timer,
                toggle_callback=self.toggle_timer,
                settings=self.settings,
                skip_callback=self.skip_break,
                open_callback=self.show_main_window_from_mini,
            )
        )

        self.floating_timer.close_requested.connect(
            self.hide_floating_timer
        )

        self.apply_theme()

        self.shortcut_manager = (
            ShortcutManager(self)
        )

        self.menu_bar_manager = (
            MenuBarManager(self)
        )

        self.native_menu = NativeMenuBar(self)
        self._setup_system_theme_watcher()

        # The compact timer follows application activation only: it is
        # shown (without activating) when the user switches to another
        # macOS app and hidden when the user returns. Both transitions
        # are visibility-only and idempotent, so they cannot steal focus,
        # raise windows, or blink. The timer runs independently.
        self._in_app_state_transition = False
        self.hide_floating_timer()
        self._setup_app_activation_watcher()

    # =========================================================
    # UI shell
    # =========================================================

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = SideNav()
        self.sidebar.setFixedWidth(172)
        shell.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        shell.addWidget(self.pages, 1)

        self.focus_view = FocusView()
        self.history_view = HistoryView(self.history.sessions)
        self.stats_view = StatsView(self.history.sessions)
        self.goals_view = GoalsView(
            self.goal_service, self.history.sessions
        )

        self._page_names = ("focus", "history", "stats", "goals")
        for view in (
            self.focus_view,
            self.history_view,
            self.stats_view,
            self.goals_view,
        ):
            self.pages.addWidget(view)

        # -----------------------------------------------------
        # Compatibility surface: FocusView owns the timer widgets
        # -----------------------------------------------------

        self.task_input = self.focus_view.task_input
        self.mode_label = self.focus_view.mode_label
        self.timer_card = self.focus_view.timer_card
        self.time_label = self.focus_view.time_label
        self.session_label = self.focus_view.session_label
        self.progress = self.focus_view.progress
        self.session_dots = self.focus_view.session_dots
        self.goal_label = self.focus_view.goal_label
        self.goal_progress = self.focus_view.goal_progress
        self.start_button = self.focus_view.start_button
        self.pause_button = self.focus_view.pause_button
        self.reset_button = self.focus_view.reset_button
        self.skip_button = self.focus_view.skip_button
        self.footer_label = self.focus_view.footer_label

    # =========================================================
    # Signals
    # =========================================================

    def connect_signals(self):
        self.focus_view.start_requested.connect(
            self.start_timer
        )

        self.focus_view.pause_requested.connect(
            self.pause_timer
        )

        self.focus_view.reset_requested.connect(
            self.reset_timer
        )

        self.focus_view.skip_requested.connect(
            self.skip_break
        )

        self.sidebar.page_requested.connect(
            self.navigate
        )

        self.sidebar.settings_requested.connect(
            self.open_settings
        )

        self.timer.tick.connect(
            self.update_display
        )

        self.timer.finished.connect(
            self.timer_finished
        )

    # =========================================================
    # Navigation
    # =========================================================

    def navigate(self, name):
        if name not in self._page_names:
            name = "focus"
        self.sidebar.set_current(name)
        self.pages.setCurrentIndex(self._page_names.index(name))
        self.refresh_current_page()

    def refresh_current_page(self):
        widget = self.pages.currentWidget()
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            try:
                refresh()
            except DatabaseError:
                pass

    # =========================================================
    # Initial timer
    # =========================================================

    def _sync_from_engine(self):
        self.mode = self.engine.mode
        self.session_number = self.engine.session_number
        self.current_task = self.engine.current_task
        self.focus_start_time = self.engine.focus_start_time

    def _on_engine_state(self):
        self._sync_from_engine()
        self._refresh_mode_ui()

    def _refresh_mode_ui(self):
        if self.engine.phase == SessionPhase.FOCUS:
            self.mode_label.setText(
                "FOCUS SESSION"
            )

        elif self.engine.phase == SessionPhase.SHORT_BREAK:
            self.mode_label.setText(
                "SHORT BREAK"
            )

        else:
            self.mode_label.setText(
                "LONG BREAK"
            )

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_mode(self.mode)

        self.update_session_information()

    def load_initial_timer(self):
        self.engine.load_initial()
        self._sync_from_engine()

        self.focus_view.hide_completion()

        self.task_input.setEnabled(True)
        self.task_input.clear()

        self._refresh_mode_ui()

        self.update_display(
            self.timer.remaining_seconds
        )

        self.update_goal_display()

    # =========================================================
    # Timer controls
    # =========================================================

    def start_timer(self):
        if self.engine.phase == SessionPhase.FOCUS:
            if not self.engine.current_task:
                task = (
                    self.task_input.text()
                    .strip()
                )

                if not task:
                    self.focus_view.show_completion(
                        "Add a focus task",
                        "Type what you want to focus on, then press Start.",
                        "Got It",
                        self.task_input.setFocus,
                    )

                    self.task_input.setFocus()

                    # The prompt above lives on the (possibly hidden)
                    # main window. Mirror it in the mini window so a
                    # Start press from the mini is never silently dead.
                    # Hint-only: never touches the timer, never shows
                    # the main window.
                    if hasattr(self, "floating_timer"):
                        try:
                            self.floating_timer.show_task_hint()
                        except Exception:
                            pass

                    return

                self.engine.capture_task(task)
                self._sync_from_engine()

                if hasattr(self, "floating_timer"):
                    self.floating_timer.set_task_name(task)

            self.task_input.setEnabled(
                False
            )

        self.focus_view.hide_completion()
        self.engine.start()
        self._sync_from_engine()

        self.update_buttons()

    def pause_timer(self):
        self.engine.pause()
        self._sync_from_engine()

        self.update_buttons()

    def toggle_timer(self):
        if self.timer.is_running():
            self.pause_timer()
        else:
            self.start_timer()

    def reset_timer(self):
        self.engine.reset_phase(clear_task=True)
        self._sync_from_engine()

        self.focus_view.hide_completion()

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_task_name("")

        self.task_input.setEnabled(
            True
        )

        self.task_input.clear()

        self.update_display(
            self.timer.remaining_seconds
        )

        self.update_buttons()

    def skip_break(self):
        """Leave the current break and prepare the next focus session."""
        if self.engine.phase == SessionPhase.FOCUS:
            return
        self.prepare_focus_session()

    # =========================================================
    # Display
    # =========================================================

    def update_display(self, seconds):
        minutes = seconds // 60

        remaining_seconds = seconds % 60

        self.time_label.setText(
            f"{minutes:02d}:{remaining_seconds:02d}"
        )

        if self.timer.total_seconds > 0:
            elapsed = (
                self.timer.total_seconds
                - seconds
            )

            self.progress.setValue(
                int(
                    elapsed
                    / self.timer.total_seconds
                    * 100
                )
            )

        self.update_buttons()
        self._sync_OS_chrome(seconds)

    def _sync_OS_chrome(self, seconds=None):
        """Push live state to tray + native menu (Group 4, never raises)."""
        if seconds is None:
            seconds = self.timer.remaining_seconds
        remaining = f"{seconds // 60:02d}:{seconds % 60:02d}"
        running = self.timer.is_running()
        is_break = self.engine.phase != SessionPhase.FOCUS
        tray = getattr(self, "menu_bar_manager", None)
        if tray is not None:
            tray.sync_state(self.mode, remaining, running)
        native = getattr(self, "native_menu", None)
        if native is not None:
            native.sync_state(running, is_break)

    def update_buttons(self):
        running = (
            self.timer.is_running()
        )

        self.start_button.setEnabled(
            not running
        )

        self.pause_button.setEnabled(
            running
        )

        self.skip_button.setVisible(
            self.engine.phase != SessionPhase.FOCUS
        )

        if hasattr(self, "floating_timer"):
            self.floating_timer.update_pause_button()
            self.floating_timer.set_break_visible(
                self.engine.phase != SessionPhase.FOCUS
            )

        self._sync_OS_chrome()

    # =========================================================
    # Timer finished
    # =========================================================

    def timer_finished(self):
        # Async fan-out (Group 4): the completion sound and the desktop
        # notification are dispatched off the handler so phase advance,
        # persistence and the next-phase UI never wait on audio backends
        # or osascript.
        self.sound_service.play_completion()

        # Backwards-compatibility fallback: legacy callers (and tests)
        # may set window.current_task directly instead of going through
        # engine.capture_task(). Stash the mirrors before the engine
        # clears its own task state.
        fallback_task = self.current_task
        fallback_start = self.focus_start_time

        result = self.engine.finish_current_phase()
        self._sync_from_engine()

        if result.completed == SessionPhase.FOCUS:
            self.save_completed_focus_session(
                task=result.task or fallback_task,
                duration_seconds=result.duration_seconds,
                start_time=(
                    result.started_at
                    if result.task
                    else (fallback_start or result.started_at)
                ),
            )

            if self.settings.get_notifications_enabled():
                self.notification_service.focus_complete()

            self.show_break_dialog(result.next_break.value)

        elif result.completed == SessionPhase.SHORT_BREAK:
            if self.settings.get_notifications_enabled():
                self.notification_service.short_break_complete()

            self.show_focus_dialog()

        else:
            if self.settings.get_notifications_enabled():
                self.notification_service.long_break_complete()

            self.show_focus_dialog()

        self.update_display(
            self.timer.remaining_seconds
        )
        self.update_buttons()

    # =========================================================
    # History
    # =========================================================

    def save_completed_focus_session(
        self,
        task=None,
        duration_seconds=None,
        start_time=None,
    ):
        task = task if task is not None else self.current_task
        if not task:
            return

        if duration_seconds is None:
            duration_seconds = (
                self.timer.total_seconds
            )

        if start_time is None:
            start_time = (
                self.focus_start_time
                or datetime.now()
            )

        try:
            end_time = start_time + timedelta(seconds=duration_seconds)
            self.history.add_focus_session(
                task=task,
                start_time=start_time.isoformat(
                    timespec="seconds"
                ),
                duration_seconds=duration_seconds,
                end_time=end_time.isoformat(timespec="seconds"),
                planned_seconds=duration_seconds,
            )
        except DatabaseError as error:
            QMessageBox.warning(
                self,
                "Focus session was not saved",
                "The timer will continue, but this completed session could "
                f"not be saved.\n\n{error}",
            )

        self._sync_from_engine()

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_task_name("")

        self.task_input.setEnabled(
            True
        )

        self.task_input.clear()

        self.update_goal_display()

    # =========================================================
    # Completion banner (non-modal; replaces blocking dialogs)
    # =========================================================

    def next_break_type(self):
        return self.engine.next_break_kind().value

    def show_break_dialog(self, break_type):
        """Show a non-blocking break prompt (kept name for compatibility)."""
        if break_type == "long":
            message = "You've completed a full focus cycle."
            action_text = "Start Long Break"
        else:
            message = "Your focus session is complete."
            action_text = "Start Short Break"

        self.navigate("focus")
        self.focus_view.show_completion(
            "Focus session complete",
            message,
            action_text,
            self.start_timer,
        )

    def show_focus_dialog(self):
        """Show a non-blocking break-over prompt."""
        self.navigate("focus")
        self.focus_view.show_completion(
            "Break complete",
            "Ready for another focus session?",
            "Start Focus",
            self.task_input.setFocus,
        )

    # =========================================================
    # Pomodoro cycle
    # =========================================================

    def start_short_break(self):
        self.prepare_break("short")
        self.engine.start()
        self._sync_from_engine()
        self.update_buttons()

    def start_long_break(self):
        self.prepare_break("long")
        self.engine.start()
        self._sync_from_engine()
        self.update_buttons()

    def start_focus(self):
        """Prepare a new focus session; starting requires an explicit click."""
        self.prepare_focus_session()

    def prepare_break(self, break_type):
        self.engine.prepare_break(BreakKind(break_type))
        self._sync_from_engine()
        self.focus_view.hide_completion()
        self.update_buttons()

    def prepare_focus_session(self):
        self.engine.prepare_focus()
        self._sync_from_engine()

        self.focus_view.hide_completion()

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_task_name("")

        self.task_input.setEnabled(True)
        self.task_input.clear()

        self.task_input.setFocus()

        self.update_buttons()

    # =========================================================
    # Mode
    # =========================================================

    def set_mode(self, mode):
        self.engine.set_mode(mode)
        self._sync_from_engine()
        self._refresh_mode_ui()

    def update_session_information(self):
        total_sessions = (
            self.settings
            .get_sessions_before_long_break()
        )

        if self.mode == "Focus":
            self.session_label.setText(
                f"Session {self.session_number} "
                f"of {total_sessions}"
            )

        elif self.mode == "Short Break":
            self.session_label.setText(
                "Short recovery"
            )

        else:
            self.session_label.setText(
                "Full cycle recovery"
            )

        self.update_session_dots()

        self.update_footer()

    def update_session_dots(self):
        total = min(
            len(self.session_dots),
            self.settings
            .get_sessions_before_long_break(),
        )

        for index, dot in enumerate(
            self.session_dots
        ):
            if index >= total:
                dot.hide()
                continue

            dot.show()

            if (
                self.mode == "Focus"
                and index + 1 == self.session_number
            ):
                dot.setProperty(
                    "active",
                    True,
                )

            elif (
                self.mode != "Focus"
                and index + 1 <= self.session_number
            ):
                dot.setProperty(
                    "active",
                    True,
                )

            else:
                dot.setProperty(
                    "active",
                    False,
                )

            dot.style().unpolish(dot)
            dot.style().polish(dot)

    # =========================================================
    # Goal
    # =========================================================

    def update_goal_display(self):
        if not self.database.is_available:
            self.goal_label.setText(
                "Session history is unavailable. Check the application data folder."
            )
            self.goal_label.setToolTip(self.database.error_message)
            self.focus_view.set_goal_progress(0, 0)
            return

        self.goal_label.setToolTip("")
        total_seconds = (
            self.history.get_today_total()
        )

        total_minutes = (
            total_seconds // 60
        )

        goal_minutes = (
            self.goal_service
            .get_daily_goal_minutes()
        )

        if total_minutes >= goal_minutes:
            self.goal_label.setText(
                f"Daily goal complete • "
                f"{total_minutes} / {goal_minutes} min"
            )

        else:
            self.goal_label.setText(
                f"Today: "
                f"{total_minutes} / "
                f"{goal_minutes} min focused"
            )

        self.focus_view.set_goal_progress(total_minutes, goal_minutes)

    # =========================================================
    # Footer
    # =========================================================

    def update_footer(self):
        focus = (
            self.settings
            .get_focus_minutes()
        )

        short_break = (
            self.settings
            .get_short_break_minutes()
        )

        long_break = (
            self.settings
            .get_long_break_minutes()
        )

        self.footer_label.setText(
            f"{focus} min focus  •  "
            f"{short_break} min short break  •  "
            f"{long_break} min long break"
        )

    # =========================================================
    # History
    # =========================================================

    def open_history(self):
        dialog = HistoryDialog(
            self.history,
            self.settings,
            self,
        )
        dialog.exec()

    def _on_goal_changed(self, key):
        if key == "daily_goal_minutes":
            self.update_goal_display()

    # =========================================================
    # Settings
    # =========================================================

    def open_settings(self):
        dialog = SettingsDialog(
            self.settings,
            self.sound_manager,
            self,
            goal_service=self.goal_service,
        )

        if (
            dialog.exec()
            == QDialog.DialogCode.Accepted
        ):
            self._apply_saved_settings(dialog)

    def _apply_saved_settings(self, dialog):
        """Apply an accepted settings dialog (testable without exec)."""
        before = (
            self.settings.get_focus_minutes(),
            self.settings.get_short_break_minutes(),
            self.settings.get_long_break_minutes(),
            self.settings.get_sessions_before_long_break(),
        )

        dialog.save_settings()

        self.notification_service.set_enabled(
            self.settings.get_notifications_enabled()
        )

        self.apply_theme()

        if hasattr(self, "floating_timer"):
            self.floating_timer.apply_opacity()

        self.update_session_information()

        self.update_goal_display()

        after = (
            self.settings.get_focus_minutes(),
            self.settings.get_short_break_minutes(),
            self.settings.get_long_break_minutes(),
            self.settings.get_sessions_before_long_break(),
        )

        # Never touch a running timer. Only re-arm an idle timer
        # when the saved durations actually changed — and preserve
        # any task text the user typed but has not started yet.
        if before != after and not self.timer.is_running():
            pending = self.task_input.text()
            self.reset_timer()
            if not self.engine.current_task and pending.strip():
                self.task_input.setText(pending)

        self.refresh_current_page()

    # =========================================================
    # Floating timer
    # =========================================================

    def show_floating_timer(self):        # Visibility-only: never touches the
        # timer and never touches the main window (no hide/show/raise
        # of the main window here). The overlay itself is shown without
        # activating the app, so it can stay on top while the user
        # works in another application.
        self.floating_timer.set_mode(
            self.mode
        )

        self.floating_timer.update_time(
            self.timer.remaining_seconds
        )

        try:
            self.floating_timer.move(
                self.floating_timer.clamp_to_visible_screen(
                    self.floating_timer.pos()
                )
            )
        except Exception:
            pass

        self.floating_timer.show_without_activating()

    def hide_floating_timer(self):
        # Hiding the mini window never quits the app, never touches
        # the timer, and never touches the main window's visibility.
        self.floating_timer.hide()
        native = getattr(self, "native_menu", None)
        if native is not None:
            native.sync_compact_visible(False)

    def show_main_window_from_mini(self):
        """Restore the main window on the explicit mini-window action.

        Shows/restores/activates the existing main window and hides
        the mini window. Never creates a window and never touches the
        timer or session state.
        """
        try:
            if self.isMinimized():
                self.showNormal()
            elif not self.isVisible():
                self.show()
        except Exception:
            pass
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
        try:
            self.hide_floating_timer()
        except Exception:
            pass

    def toggle_floating_timer(self):
        """Toggle the mini window (native Window menu entry point)."""
        try:
            visible = self.floating_timer.isVisible()
        except Exception:
            visible = False
        if visible:
            self.hide_floating_timer()
        else:
            self.show_floating_timer()
            native = getattr(self, "native_menu", None)
            if native is not None:
                native.sync_compact_visible(True)

    def show_about(self):
        """Standard About box (native app-menu entry point)."""
        from app import __version__

        QMessageBox.about(
            self,
            "About Focus Flow",
            f"<b>Focus Flow {__version__}</b><br><br>"
            "A Pomodoro productivity timer for macOS.<br>"
            "Focus deeply. Rest intentionally.",
        )

    def sync_floating_timer_visibility(self, app_is_active=None):
        """Follow application activation without stealing focus.

        Kept as a public entry point (and for backward compatibility):
        True hides the mini window, False/None shows it via
        ``show_without_activating``. Both paths are idempotent and never
        touch the timer or raise/activate any window.
        """
        if app_is_active:
            self._on_app_activated()
        else:
            self._on_app_deactivated()
        return None

    def _setup_app_activation_watcher(self):
        # Application-level state (not window activation) drives the mini
        # window: window-activation signals re-fire when we show/hide the
        # overlay and caused the macOS blink/raise loop. Application state
        # does not change when a WA_ShowWithoutActivating Tool window is
        # shown, so this cannot self-trigger.
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.applicationStateChanged.connect(
                    self._on_application_state_changed
                )
        except Exception:
            pass

    def _on_application_state_changed(self, state):
        try:
            from PySide6.QtCore import Qt

            if state == Qt.ApplicationState.ApplicationActive:
                self._on_app_activated()
            else:
                self._on_app_deactivated()
        except Exception:
            pass

    def _pointer_over_mini(self):
        """True when the pointer is currently over the mini window.

        The mini is deliberately non-focusable (``WindowDoesNotAcceptFocus``
        + ``NoFocus`` + ``WA_ShowWithoutActivating``), so on macOS it never
        becomes ``QApplication.activeWindow()`` and ``isActiveWindow()`` is
        always False for it. The pre-existing ``activeWindow() is floating``
        guard is therefore dead on macOS: a click on the mini still
        activates the *application*, the guard misses it, and the handler
        below hides the mini and re-shows the main window (preempting the
        button/drag/close click). Pointer geometry works regardless of
        focus, so it reliably identifies mini-originated activations.
        """
        floating = getattr(self, "floating_timer", None)
        if floating is None:
            return False
        try:
            if not floating.isVisible():
                return False
        except Exception:
            return False
        try:
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QApplication

            try:
                pos = QCursor.pos()
            except Exception:
                pos = None
            if pos is None:
                return False
            try:
                if floating.frameGeometry().contains(pos):
                    return True
            except Exception:
                pass
            try:
                widget = QApplication.widgetAt(pos)
                while widget is not None:
                    if widget is floating:
                        return True
                    widget = widget.parentWidget()
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _on_app_deactivated(self):
        # Another app is now frontmost: show the already-built mini window
        # without activating Focus Flow and hide the main window so an
        # OS-level bring-to-front on the next mini click has no main window
        # to pop forward. Guarded so repeated events never re-show,
        # flicker, or move the window.
        if getattr(self, "_in_app_state_transition", False):
            return
        try:
            if self.floating_timer.isVisible():
                try:
                    if self.isVisible() and not self.isMinimized():
                        self.hide()
                except Exception:
                    pass
                return
        except Exception:
            pass
        self._in_app_state_transition = True
        try:
            try:
                if self.isVisible() and not self.isMinimized():
                    self.hide()
            except Exception:
                pass
            self.show_floating_timer()
        finally:
            self._in_app_state_transition = False

    def _on_app_activated(self):
        # User returned: hide the mini window. The main window is already
        # frontmost via macOS; never raise/activate here. Restore it only
        # if it was minimized or hidden.
        if getattr(self, "_in_app_state_transition", False):
            return
        # Clicking the mini window itself activates the app on platforms
        # where the non-activating flag is not honored. That interaction
        # must not hide the mini or restore the main window: only proceed
        # when the main window (not the mini) took activation.
        try:
            from PySide6.QtWidgets import QApplication

            floating = getattr(self, "floating_timer", None)
            if floating is not None:
                if QApplication.activeWindow() is floating:
                    return
                try:
                    if floating.isActiveWindow():
                        return
                except Exception:
                    pass
        except Exception:
            pass
        # The focus-based guard above is dead on macOS: the mini is
        # WindowDoesNotAcceptFocus/NoFocus by design, so it never becomes
        # the active window even when its click activated the app. Fall
        # back to pointer geometry, which is focus-independent.
        try:
            if self._pointer_over_mini():
                return
        except Exception:
            pass
        self._in_app_state_transition = True
        try:
            try:
                if self.floating_timer.isVisible():
                    self.hide_floating_timer()
            except Exception:
                pass
            try:
                if self.isMinimized():
                    self.showNormal()
                elif not self.isVisible():
                    self.show()
            except Exception:
                pass
        finally:
            self._in_app_state_transition = False

    def changeEvent(self, event):
        super().changeEvent(event)
        # The app-level watcher misses the case where the app is already
        # active (e.g. activated by a mini-window click that we ignored)
        # and the user then clicks the main window: no application state
        # change fires. Window-level activation covers it — hide the mini
        # without touching the timer or raising anything.
        try:
            from PySide6.QtCore import QEvent

            if (
                event.type() == QEvent.Type.ActivationChange
                and self.isActiveWindow()
            ):
                try:
                    if self._pointer_over_mini():
                        # Main became active but the pointer is over the
                        # mini (mini click that also made main key because
                        # the mini refuses focus): keep the mini.
                        return
                except Exception:
                    pass
                try:
                    if self.floating_timer.isVisible():
                        self.hide_floating_timer()
                except Exception:
                    pass
        except Exception:
            pass

    # =========================================================
    # Application
    # =========================================================

    def close_application(self):
        try:
            self.notification_service.shutdown()
        except Exception:
            pass

        self.floating_timer.close()

        self.database.close()

        self.close()

    def closeEvent(self, event):
        try:
            self.hide_floating_timer()
        except Exception:
            pass

        try:
            self.notification_service.shutdown()
        except Exception:
            pass

        self.database.close()

        event.accept()

    # =========================================================
    # Theme
    # =========================================================

    def apply_theme(self):
        resolved = theme_service.resolve(
            self.settings.get_theme(),
            self.settings.get_accent_color(),
            self.settings.get_background_color(),
        )

        theme = resolved["tokens"]
        accent = resolved["accent"]

        if hasattr(self, "floating_timer"):
            self.floating_timer.apply_theme(resolved)

        self.setStyleSheet(
            theme_service.build_main_window_stylesheet(resolved)
            + theme_service.build_shell_stylesheet(resolved)
        )

        if hasattr(self, "stats_view"):
            self.stats_view.chart.set_colors(
                accent,
                theme["surface_alt"],
                theme["secondary_text"],
            )
            self.stats_view.streak_strip.set_colors(
                accent,
                theme["border"],
                theme["secondary_text"],
            )

        self.update_session_dots()
        self.refresh_current_page()

    # =========================================================
    # Follow System theme (Group 4)
    # =========================================================

    def _setup_system_theme_watcher(self):
        """Re-resolve the palette when macOS light/dark mode changes."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            hints = app.styleHints() if app is not None else None
            if hints is not None and hasattr(
                hints, "colorSchemeChanged"
            ):
                hints.colorSchemeChanged.connect(
                    self._on_system_color_scheme_changed
                )
        except Exception:
            pass

    def _on_system_color_scheme_changed(self, _scheme):
        try:
            if self.settings.get_theme() == "System":
                self.apply_theme()
        except Exception:
            pass
