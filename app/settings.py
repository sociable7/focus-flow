"""Backwards-compatible alias for the typed settings store.

Group 1: ``AppSettings`` is now ``SettingsStore`` with validation and a
``valueChanged`` signal. Existing imports (``app.settings.AppSettings``)
keep working unchanged, including the test pattern that patches
``app.settings.QSettings`` with a temp-dir factory: this subclass
resolves ``QSettings`` through its own module globals so the patch
takes effect.
"""

from PySide6.QtCore import QSettings

from app.services.settings_store import SettingsStore


__all__ = ["AppSettings", "QSettings", "SettingsStore"]


class AppSettings(SettingsStore):
    def __init__(self):
        super().__init__(
            QSettings(
                "Focus Flow",
                "Focus Flow",
            )
        )
