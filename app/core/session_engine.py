from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from app.core.enums import BreakKind, SessionPhase, phase_from_mode


@dataclass
class PhaseResult:
    """Outcome of finishing the current phase."""

    completed: SessionPhase
    task: str = ""
    duration_seconds: int = 0
    started_at: datetime | None = None
    next_break: BreakKind | None = None


class SessionEngine(QObject):
    """Single source of truth for timer state and transitions.

    The engine owns phase, cycle position, current task, planned and
    remaining durations, and running/paused state. It drives the shared
    ``Clock`` but never auto-starts it: every transition ends paused and
    the user (or an explicit programmatic call) starts the next phase.

    ``MainWindow`` keeps thin mirror attributes (``mode``,
    ``session_number``, ``current_task``, ``focus_start_time``) for
    backwards compatibility; they are synced from the engine after each
    mutation. New code should read the engine directly.
    """

    stateChanged = Signal()

    def __init__(self, clock, settings):
        super().__init__()
        self._clock = clock
        self._settings = settings

        self._phase = SessionPhase.FOCUS
        self._cycle_pos = 1
        self._task = ""
        self._focus_start = None

    # =====================================================
    # Read-only state
    # =====================================================

    @property
    def phase(self):
        return self._phase

    @property
    def mode(self):
        return self._phase.value

    @property
    def session_number(self):
        return self._cycle_pos

    @property
    def current_task(self):
        return self._task

    @property
    def focus_start_time(self):
        return self._focus_start

    @property
    def remaining_seconds(self):
        return self._clock.remaining_seconds

    @property
    def total_seconds(self):
        return self._clock.total_seconds

    def is_running(self):
        return self._clock.is_running()

    def cycle_length(self):
        try:
            return max(
                1,
                int(
                    self._settings
                    .get_sessions_before_long_break()
                ),
            )
        except (TypeError, ValueError):
            return 4

    # =====================================================
    # Setup
    # =====================================================

    def load_initial(self):
        self._phase = SessionPhase.FOCUS
        self._cycle_pos = 1
        self._task = ""
        self._focus_start = None
        self._clock.reset(
            self._phase_seconds(SessionPhase.FOCUS)
        )
        self.stateChanged.emit()

    def set_mode(self, mode):
        self._phase = phase_from_mode(mode)
        self.stateChanged.emit()

    # =====================================================
    # Durations
    # =====================================================

    def _phase_seconds(self, phase):
        if phase == SessionPhase.SHORT_BREAK:
            minutes = self._settings.get_short_break_minutes()
        elif phase == SessionPhase.LONG_BREAK:
            minutes = self._settings.get_long_break_minutes()
        else:
            minutes = self._settings.get_focus_minutes()
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 25
        return max(0, minutes * 60)

    # =====================================================
    # Controls
    # =====================================================

    def capture_task(self, task_text):
        """Capture the focus task. Returns False when no task given."""
        if self._phase != SessionPhase.FOCUS:
            return True
        if self._task:
            return True
        task = (task_text or "").strip()
        if not task:
            return False
        self._task = task
        self._focus_start = datetime.now()
        self.stateChanged.emit()
        return True

    def start(self):
        self._clock.start()
        self.stateChanged.emit()

    def pause(self):
        self._clock.pause()
        self.stateChanged.emit()

    def toggle(self):
        if self._clock.is_running():
            self.pause()
        else:
            self.start()

    def reset_phase(self, clear_task=True):
        """Pause and re-arm the current phase clock without changing phase."""
        self._clock.pause()
        if clear_task:
            self._task = ""
            self._focus_start = None
        self._clock.reset(
            self._phase_seconds(self._phase)
        )
        self.stateChanged.emit()

    # =====================================================
    # Transitions (never auto-start)
    # =====================================================

    def next_break_kind(self):
        if self._cycle_pos >= self.cycle_length():
            return BreakKind.LONG
        return BreakKind.SHORT

    def prepare_break(self, break_kind):
        if break_kind == BreakKind.LONG:
            self._phase = SessionPhase.LONG_BREAK
        else:
            self._phase = SessionPhase.SHORT_BREAK
        self._clock.reset(
            self._phase_seconds(self._phase)
        )
        self.stateChanged.emit()

    def prepare_focus(self):
        if self._cycle_pos >= self.cycle_length():
            self._cycle_pos = 1
        else:
            self._cycle_pos += 1
        self._phase = SessionPhase.FOCUS
        self._task = ""
        self._focus_start = None
        self._clock.reset(
            self._phase_seconds(self._phase)
        )
        self.stateChanged.emit()

    def finish_current_phase(self):
        """Advance after the clock fires ``finished``.

        Returns a PhaseResult describing what completed so the caller
        can persist/notify/dialog exactly once.
        """
        if self._phase == SessionPhase.FOCUS:
            result = PhaseResult(
                completed=SessionPhase.FOCUS,
                task=self._task,
                duration_seconds=self._clock.total_seconds,
                started_at=self._focus_start or datetime.now(),
                next_break=self.next_break_kind(),
            )
            self._task = ""
            self._focus_start = None
            self.prepare_break(result.next_break)
            return result

        completed = self._phase
        self.prepare_focus()
        return PhaseResult(completed=completed)
