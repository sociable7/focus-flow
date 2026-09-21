"""Asynchronous completion-sound dispatch (Group 4).

``SoundManager`` (``app.sounds``) remains the synchronous playback engine
and its API is unchanged. ``SoundService`` sits above it and posts every
playback request to the Qt event loop with ``QTimer.singleShot(0, ...)``
so the timer-finished handler never waits on media-load checks or file
probes, no matter how slow the audio backend is.
"""

from PySide6.QtCore import QObject, QTimer, Signal


class SoundService(QObject):
    """Non-blocking facade over ``SoundManager``."""

    played = Signal(str)

    def __init__(self, manager, settings=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.settings = settings

    def play_completion(self):
        """Play the configured completion sound asynchronously."""
        if self.settings is None:
            return
        try:
            sound = self.settings.get_sound()
            custom = self.settings.get_custom_sound()
        except Exception:
            return
        QTimer.singleShot(
            0,
            lambda: self._play(sound, custom),
        )

    def preview(self, sound_name, custom_sound=""):
        """Synchronous preview for the settings dialog's Test button."""
        try:
            return bool(self.manager.play(sound_name, custom_sound))
        except Exception:
            return False

    def _play(self, sound_name, custom_sound=""):
        try:
            ok = self.manager.play(sound_name, custom_sound)
        except Exception:
            return
        if ok:
            try:
                self.played.emit(sound_name)
            except Exception:
                pass
