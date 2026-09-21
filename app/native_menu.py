"""Native macOS menu bar (Group 4).

Provides the standard application menu (About, Preferences, Quit),
timer controls, view navigation and window actions through Qt roles so
macOS places them correctly (app menu, Cmd-,/Cmd-Q/H/M shortcuts). All
actions delegate to existing ``MainWindow`` slots; nothing here owns
timer or session state.
"""

from PySide6.QtGui import QAction, QKeySequence


class NativeMenuBar:
    """Builds ``window.menuBar()`` menus and keeps labels in sync."""

    def __init__(self, window):
        self.window = window
        self._build()

    # =====================================================
    # Construction
    # =====================================================

    def _build(self):
        window = self.window
        bar = window.menuBar()

        # -------------------------------------------------
        # Application menu (macOS shows this as the app menu)
        # -------------------------------------------------

        app_menu = bar.addMenu("Focus Flow")

        about = QAction("About Focus Flow", window)
        about.setMenuRole(QAction.MenuRole.AboutRole)
        about.triggered.connect(window.show_about)
        app_menu.addAction(about)

        app_menu.addSeparator()

        preferences = QAction("Settings…", window)
        preferences.setMenuRole(QAction.MenuRole.PreferencesRole)
        preferences.triggered.connect(window.open_settings)
        app_menu.addAction(preferences)

        app_menu.addSeparator()

        quit_app = QAction("Quit Focus Flow", window)
        quit_app.setMenuRole(QAction.MenuRole.QuitRole)
        quit_app.triggered.connect(window.close_application)
        app_menu.addAction(quit_app)

        # -------------------------------------------------
        # Timer
        # -------------------------------------------------

        timer_menu = bar.addMenu("Timer")

        self.toggle_action = QAction("Start", window)
        self.toggle_action.setShortcut(QKeySequence("Ctrl+T"))
        self.toggle_action.triggered.connect(window.toggle_timer)
        timer_menu.addAction(self.toggle_action)

        reset_action = QAction("Reset Timer", window)
        reset_action.triggered.connect(window.reset_timer)
        timer_menu.addAction(reset_action)

        self.skip_action = QAction("Skip Break", window)
        self.skip_action.triggered.connect(window.skip_break)
        timer_menu.addAction(self.skip_action)

        # -------------------------------------------------
        # View
        # -------------------------------------------------

        view_menu = bar.addMenu("View")

        for index, name in enumerate(
            ("focus", "history", "stats", "goals")
        ):
            action = QAction(f"Go to {name.capitalize()}", window)
            action.setShortcut(QKeySequence(f"Ctrl+{index + 1}"))
            action.triggered.connect(
                lambda _checked=False, page=name: window.navigate(page)
            )
            view_menu.addAction(action)

        # -------------------------------------------------
        # Window
        # -------------------------------------------------

        window_menu = bar.addMenu("Window")

        minimize_action = QAction("Minimize", window)
        minimize_action.setShortcut(QKeySequence("Ctrl+M"))
        minimize_action.triggered.connect(window.showMinimized)
        window_menu.addAction(minimize_action)

        self.compact_action = QAction("Show Compact Timer", window)
        self.compact_action.triggered.connect(
            window.toggle_floating_timer
        )
        window_menu.addAction(self.compact_action)

        bring_all = QAction("Bring All to Front", window)
        bring_all.triggered.connect(window.show)
        window_menu.addAction(bring_all)

    # =====================================================
    # State sync (called alongside the tray sync; never raises)
    # =====================================================

    def sync_state(self, running=False, is_break=False):
        try:
            self.toggle_action.setText("Pause" if running else "Start")
            self.skip_action.setEnabled(is_break)
        except Exception:
            pass

    def sync_compact_visible(self, visible):
        try:
            self.compact_action.setText(
                "Hide Compact Timer" if visible else "Show Compact Timer"
            )
        except Exception:
            pass
