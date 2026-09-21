"""Asynchronous macOS notification delivery (Group 4).

``NotificationManager`` (``app.notifications``) shells out to
``osascript`` synchronously, which can block the GUI thread for hundreds
of milliseconds. ``NotificationService`` keeps that manager as the
delivery engine but runs it on a dedicated worker thread: ``post()``
returns immediately and the AppleScript process runs off the event loop.
Delivery is best-effort and — like the manager itself — never raises.
"""

import logging

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.notifications import NotificationManager

LOGGER = logging.getLogger(__name__)


class _NotificationWorker(QObject):
    _deliver = Signal(str, str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._deliver.connect(self._on_deliver)

    @Slot(str, str)
    def _on_deliver(self, title, message):
        try:
            self.manager.show(title, message)
        except Exception:
            LOGGER.exception("Notification delivery failed")


class NotificationService(QObject):
    """Threaded facade over ``NotificationManager``."""

    def __init__(self, manager=None, parent=None):
        super().__init__(parent)
        self.manager = (
            manager if manager is not None else NotificationManager()
        )
        self._enabled = True
        self._thread = QThread(self)
        self._worker = _NotificationWorker(self.manager)
        self._worker.moveToThread(self._thread)
        self._thread.start()

    # =====================================================
    # Control
    # =====================================================

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)

    def is_enabled(self):
        return self._enabled

    # =====================================================
    # Delivery (all non-blocking, never raise)
    # =====================================================

    def post(self, title, message):
        """Queue a notification; returns False when dropped/disabled."""
        try:
            if not self._enabled:
                return False
            if not self._thread.isRunning():
                return False
            self._worker._deliver.emit(str(title), str(message))
            return True
        except Exception:
            LOGGER.exception("Queueing notification failed")
            return False

    def focus_complete(self):
        return self.post("Focus session complete", "Time for a break.")

    def short_break_complete(self):
        return self.post("Break finished", "Ready to focus again?")

    def long_break_complete(self):
        return self.post(
            "Long break finished", "Ready for another focus session?"
        )

    # =====================================================
    # Teardown
    # =====================================================

    def shutdown(self):
        """Stop the worker thread (idempotent, never raises)."""
        try:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)
        except Exception:
            LOGGER.exception("Stopping notification thread failed")
