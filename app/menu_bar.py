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

        self.tray.show()