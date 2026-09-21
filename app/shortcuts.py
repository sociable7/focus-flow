from PySide6.QtGui import QKeySequence, QShortcut


class ShortcutManager:
    """Application shortcuts that never consume normal text entry."""

    def __init__(self, window):
        self.window = window
        self.start_pause = self._create_shortcuts(
            ("Ctrl+Space", "Meta+Space"),
            window.toggle_timer,
        )
        self.reset = self._create_shortcuts(
            ("Ctrl+R", "Meta+R"),
            window.reset_timer,
        )

    def _create_shortcuts(self, sequences, callback):
        shortcuts = []
        for sequence in sequences:
            shortcut = QShortcut(QKeySequence(sequence), self.window)
            shortcut.activated.connect(callback)
            shortcuts.append(shortcut)
        return shortcuts
