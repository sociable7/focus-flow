from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMenu,
    QSystemTrayIcon,
)


class MenuBarManager:
    """
    Provides a macOS system status-bar menu
    for quick Focus Flow controls.
    """

    def __init__(self, window):
        self.window = window

        self.tray = QSystemTrayIcon(
            window
        )

        icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "icons"
            / "settings.svg"
        )

        self.tray.setIcon(
            QIcon(str(icon_path))
        )

        menu = QMenu()

        start_action = menu.addAction(
            "Start / Pause"
        )

        start_action.triggered.connect(
            window.toggle_timer
        )

        reset_action = menu.addAction(
            "Reset"
        )

        reset_action.triggered.connect(
            window.reset_timer
        )

        menu.addSeparator()

        show_action = menu.addAction(
            "Show Focus Flow"
        )

        show_action.triggered.connect(
            window.show
        )

        compact_action = menu.addAction(
            "Show Compact Timer"
        )

        compact_action.triggered.connect(
            window.show_floating_timer
        )

        menu.addSeparator()

        quit_action = menu.addAction(
            "Quit Focus Flow"
        )

        quit_action.triggered.connect(
            window.close_application
        )

        self.tray.setContextMenu(menu)

        self.start_action = start_action
        self.compact_action = compact_action

        self.tray.show()

    # =====================================================
    # Tray service (Group 4): reflect live timer state
    # =====================================================

    def sync_state(self, mode_text="", remaining_text="", running=False):
        """Update tooltip and Start/Pause label; never raises."""
        try:
            state = "Running" if running else "Paused"
            detail = f"{mode_text} {remaining_text}".strip()
            if detail:
                self.tray.setToolTip(f"Focus Flow — {detail} ({state})")
            else:
                self.tray.setToolTip(f"Focus Flow ({state})")
            self.start_action.setText("Pause" if running else "Start")
        except Exception:
            pass