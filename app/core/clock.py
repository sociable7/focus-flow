import time

from PySide6.QtCore import QObject, QTimer, Signal


class Clock(QObject):
    """Monotonic 1-second countdown clock.

    Public API mirrors the legacy ``PomodoroTimer`` so existing callers
    (main window, floating timer, tests) keep working:

    - inert after finishing: ``start()`` no-ops at 0
    - exactly one ``finished`` per ``reset()``
    - ``tick`` emits remaining seconds on every change

    Drift correction: the wall-clock deadline is recorded on ``start()``
    and each timeout snaps ``remaining_seconds`` back to the deadline when
    the event loop is late by more than a small tolerance. Manual
    ``_on_tick()`` calls (as used in tests) still decrement by exactly
    one second.
    """

    tick = Signal(int)
    finished = Signal()

    _DRIFT_TOLERANCE_SECONDS = 2

    def __init__(self):
        super().__init__()

        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(
            self._on_tick
        )

        self.remaining_seconds = 0
        self.total_seconds = 0
        self._deadline = None

    def start(self):
        if self.remaining_seconds > 0:
            self._deadline = (
                time.monotonic() + self.remaining_seconds
            )
            self._timer.start()

    def pause(self):
        self._timer.stop()
        if self._deadline is not None:
            remaining = self._deadline - time.monotonic()
            # Clamp rather than trust a stale deadline: pausing must
            # never extend or lose the displayed remaining time.
            self.remaining_seconds = max(
                0,
                min(
                    self.remaining_seconds,
                    int(round(remaining)),
                ),
            )
        self._deadline = None

    def reset(self, seconds):
        self._timer.stop()
        self._deadline = None

        self.total_seconds = seconds
        self.remaining_seconds = seconds

        self.tick.emit(
            self.remaining_seconds
        )

    def is_running(self):
        return self._timer.isActive()

    def _on_tick(self):
        # A completed clock is inert until its owner explicitly resets it.
        # This guarantees one finished signal per clock reset.
        if self.remaining_seconds <= 0:
            self._timer.stop()
            self._deadline = None
            return

        if self._deadline is not None:
            deadline_remaining = int(
                round(self._deadline - time.monotonic())
            )
            drift = self.remaining_seconds - 1 - deadline_remaining
            if abs(drift) >= self._DRIFT_TOLERANCE_SECONDS:
                self.remaining_seconds = max(
                    0,
                    deadline_remaining,
                )
                self.tick.emit(
                    self.remaining_seconds
                )
                if self.remaining_seconds == 0:
                    self._timer.stop()
                    self._deadline = None
                    self.finished.emit()
                return

        self.remaining_seconds -= 1

        self.tick.emit(
            self.remaining_seconds
        )

        if self.remaining_seconds == 0:
            self._timer.stop()
            self._deadline = None
            self.finished.emit()
