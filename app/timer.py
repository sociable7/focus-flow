from PySide6.QtCore import QObject, QTimer, Signal


class PomodoroTimer(QObject):
    tick = Signal(int)
    finished = Signal()

    def __init__(self):
        super().__init__()

        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(
            self._on_tick
        )

        self.remaining_seconds = 0
        self.total_seconds = 0

    def start(self):
        if self.remaining_seconds > 0:
            self._timer.start()

    def pause(self):
        self._timer.stop()

    def reset(self, seconds):
        self._timer.stop()

        self.total_seconds = seconds
        self.remaining_seconds = seconds

        self.tick.emit(
            self.remaining_seconds
        )

    def is_running(self):
        return self._timer.isActive()

    def _on_tick(self):
        # A completed timer is inert until its owner explicitly resets it.
        # This guarantees one finished signal per timer reset.
        if self.remaining_seconds <= 0:
            self._timer.stop()
            return

        self.remaining_seconds -= 1

        self.tick.emit(
            self.remaining_seconds
        )

        if self.remaining_seconds == 0:
            self._timer.stop()
            self.finished.emit()
