"""Central theme resolution and stylesheet generation.

Group 1 centralizes the previously duplicated per-dialog theme logic.
Token values are byte-identical to the prototype palettes; this service
only removes duplication, it does not redesign anything.
"""

from app.themes import THEMES, get_theme


#: Theme name that tracks the macOS system appearance (Group 4).
SYSTEM_THEME_NAME = "System"


def system_theme_name():
    """Concrete theme backing ``System``: light → Minimal, dark → Midnight.

    Falls back to Midnight when the platform cannot report a color
    scheme (offscreen tests, non-macOS, older Qt). Never raises.
    """
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        hints = app.styleHints() if app is not None else None
        scheme = hints.colorScheme() if hints is not None else None
        if scheme == Qt.ColorScheme.Light:
            return "Minimal"
    except Exception:
        pass
    return "Midnight"


def resolve(theme_name="", accent_override="", background_override=""):
    """Resolve effective tokens plus background/accent overrides.

    ``System`` (or an empty name falling back to the default) resolves
    through :func:`system_theme_name` so the UI tracks macOS light/dark
    mode; every other name behaves exactly as before.
    """
    if theme_name == SYSTEM_THEME_NAME:
        effective_name = system_theme_name()
    else:
        effective_name = theme_name or "Midnight"
    theme = get_theme(effective_name)
    background = background_override or theme["background"]
    accent = accent_override or theme["accent"]
    return {
        "name": (
            theme_name
            if theme_name in THEMES or theme_name == SYSTEM_THEME_NAME
            else "Midnight"
        ),
        "tokens": dict(theme),
        "background": background,
        "accent": accent,
    }


def build_main_window_stylesheet(resolved):
    theme = resolved["tokens"]
    background = resolved["background"]
    accent = resolved["accent"]
    return f"""
            QMainWindow {{
                background: {background};
            }}

            QWidget {{
                color: {theme["text"]};
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    "Helvetica Neue",
                    sans-serif;
            }}

            QLabel#appTitle {{
                font-size: 25px;
                font-weight: 700;
            }}

            QLabel#appSubtitle {{
                color: {theme["secondary_text"]};
                font-size: 12px;
            }}

            QLabel#taskLabel {{
                color: {theme["secondary_text"]};
                font-size: 12px;
                font-weight: 600;
            }}

            QLineEdit#taskInput {{
                background: {theme["input"]};
                color: {theme["input_text"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 13px;
            }}

            QLineEdit#taskInput:focus {{
                border: 2px solid {accent};
            }}

            QPushButton#settingsButton {{
                background: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
            }}

            QPushButton#settingsButton:hover {{
                background: {theme["surface_alt"]};
            }}

            QLabel#modeLabel {{
                color: {accent};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 2px;
            }}

            QFrame#timerCard {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 28px;
            }}

            QLabel#timeLabel {{
                font-size: 88px;
                font-weight: 300;
            }}

            QLabel#sessionLabel {{
                color: {theme["secondary_text"]};
                font-size: 13px;
                font-weight: 500;
            }}

            QProgressBar#progressBar {{
                background: {theme["surface_alt"]};
                border: none;
                border-radius: 3px;
            }}

            QProgressBar#progressBar::chunk {{
                background: {accent};
                border-radius: 3px;
            }}

            QFrame#sessionDot {{
                background: {theme["border"]};
                border-radius: 4px;
            }}

            QFrame#sessionDot[active="true"] {{
                background: {accent};
            }}

            QLabel#goalLabel {{
                color: {theme["secondary_text"]};
                font-size: 11px;
                font-weight: 600;
            }}

            QPushButton {{
                border-radius: 12px;
                min-height: 44px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 650;
            }}

            QPushButton#primaryButton {{
                background: {accent};
                color: {theme["button_text"]};
                border: none;
            }}

            QPushButton#primaryButton:disabled {{
                background: {theme["border"]};
                color: {theme["secondary_text"]};
            }}

            QPushButton#secondaryButton {{
                background: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
            }}

            QPushButton#secondaryButton:hover {{
                background: {theme["surface_alt"]};
            }}

            QPushButton#secondaryButton:disabled {{
                color: {theme["secondary_text"]};
            }}

            QLabel#footerLabel {{
                color: {theme["secondary_text"]};
                font-size: 11px;
            }}
            """


def _is_dark_surface(surface):
    """True when a ``#RRGGBB`` surface token is visually dark.

    Only dark themes need an explicit combo-popup background; light
    themes already render the popup with the correct system light
    palette, so styling them would alter Light mode.
    """
    try:
        red = int(surface[1:3], 16)
        green = int(surface[3:5], 16)
        blue = int(surface[5:7], 16)
    except (TypeError, ValueError):
        return False
    return 0.299 * red + 0.587 * green + 0.114 * blue < 128


def build_shell_stylesheet(resolved):
    """Sidebar, pages, cards, tables, inputs and completion banner."""
    theme = resolved["tokens"]
    background = resolved["background"]
    accent = resolved["accent"]
    # Combo dropdown lists (History's "All time" / "All tasks" filters)
    # have no themed background of their own: without a rule they keep
    # Qt's system light palette while inheriting the theme's light text,
    # which is unreadable in Dark mode. Light themes are left untouched
    # so their popup keeps its existing appearance byte for byte; the
    # values below mirror the Settings dialog's popup rule.
    combo_popup = ""
    if _is_dark_surface(theme["surface"]):
        combo_popup = f"""
            QComboBox QAbstractItemView {{
                background: {theme["surface"]};
                color: {theme["text"]};
                selection-background-color:
                    {accent};
                selection-color:
                    {theme["button_text"]};
            }}
"""
    return f"""
            QFrame#sideBar {{
                background: {theme["surface"]};
                border-right: 1px solid {theme["border"]};
            }}

            QLabel#brandLabel {{
                font-size: 15px;
                font-weight: 700;
            }}

            QPushButton#navButton {{
                background: transparent;
                color: {theme["secondary_text"]};
                border: none;
                border-radius: 9px;
                padding: 9px 12px;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
            }}

            QPushButton#navButton:hover {{
                background: {theme["surface_alt"]};
                color: {theme["text"]};
            }}

            QPushButton#navButton:checked {{
                background: {theme["surface_alt"]};
                color: {accent};
            }}

            QPushButton#settingsNavButton {{
                background: transparent;
                color: {theme["secondary_text"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }}

            QPushButton#settingsNavButton:hover {{
                background: {theme["surface_alt"]};
                color: {theme["text"]};
            }}

            QLabel#pageTitle {{
                font-size: 22px;
                font-weight: 700;
            }}

            QLabel#pageSubtitle {{
                color: {theme["secondary_text"]};
                font-size: 12px;
            }}

            QLabel#sectionTitle {{
                font-size: 14px;
                font-weight: 700;
            }}

            QFrame#statCard {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#statTitle {{
                color: {theme["secondary_text"]};
                font-size: 11px;
                font-weight: 600;
            }}

            QLabel#statValue {{
                font-size: 19px;
                font-weight: 700;
            }}

            QFrame#editorCard {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QFrame#completionBanner {{
                background: {theme["surface"]};
                border: 1px solid {accent};
                border-radius: 14px;
            }}

            QLabel#bannerTitle {{
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#bannerMessage {{
                color: {theme["secondary_text"]};
                font-size: 12px;
            }}

            QLabel#noticeLabel {{
                color: {theme["secondary_text"]};
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#pageLabel {{
                color: {theme["secondary_text"]};
                font-size: 12px;
                font-weight: 600;
            }}

            QLineEdit#searchInput {{
                background: {theme["input"]};
                color: {theme["input_text"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 8px 12px;
                font-size: 13px;
            }}

            QLineEdit#searchInput:focus {{
                border: 2px solid {accent};
            }}

            QComboBox#filterCombo,
            QSpinBox {{
                background: {theme["input"]};
                color: {theme["input_text"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 7px 10px;
                min-height: 20px;
            }}
{combo_popup}
            QTableWidget#dataTable {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
                gridline-color: {theme["border"]};
                alternate-background-color: {theme["surface_alt"]};
            }}

            QHeaderView::section {{
                background: {theme["surface_alt"]};
                color: {theme["secondary_text"]};
                border: none;
                border-bottom: 1px solid {theme["border"]};
                padding: 9px;
                font-weight: 700;
            }}

            QTableWidget::item {{
                padding: 7px;
            }}

            QTableWidget::item:selected {{
                background: {accent};
                color: {theme["button_text"]};
            }}

            QProgressBar#goalProgressBar {{
                background: {theme["surface_alt"]};
                border: none;
                border-radius: 2px;
            }}

            QProgressBar#goalProgressBar::chunk {{
                background: {accent};
                border-radius: 2px;
            }}

            QProgressBar#taskRowBar {{
                background: {theme["surface_alt"]};
                border: none;
                border-radius: 4px;
            }}

            QProgressBar#taskRowBar::chunk {{
                background: {accent};
                border-radius: 4px;
            }}

            QLabel#taskRowName {{
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#taskRowValue {{
                color: {theme["secondary_text"]};
                font-size: 12px;
                font-weight: 600;
            }}

            QMainWindow {{
                background: {background};
            }}
            """


def build_floating_stylesheet(resolved):
    """Compact floating timer: same tokens as the main timer card."""
    theme = resolved["tokens"]
    accent = resolved["accent"]
    return f"""
            FloatingTimer {{
                background: transparent;
            }}

            QWidget {{
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    "Helvetica Neue",
                    sans-serif;
            }}

            QFrame#floatingContainer {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}

            QLabel#modeLabel {{
                color: {accent};
                font-size: 10px;
                font-weight: 800;
            }}

            QLabel#timeLabel {{
                color: {theme["text"]};
                background: transparent;
            }}

            QLabel#taskLabel {{
                color: {theme["secondary_text"]};
                font-size: 11px;
                font-weight: 500;
            }}

            QPushButton#closeButton {{
                color: {theme["secondary_text"]};
                background: transparent;
                border: none;
                font-size: 18px;
                border-radius: 12px;
            }}

            QPushButton#closeButton:hover {{
                background: {theme["surface_alt"]};
                color: {theme["text"]};
            }}

            QPushButton#pauseButton {{
                color: {theme["button_text"]};
                background: {accent};
                border: none;
                border-radius: 8px;
                padding: 6px;
                font-weight: 600;
            }}

            QPushButton#pauseButton:hover {{
                background: {accent};
            }}

            QPushButton#pauseButton:disabled {{
                background: {theme["border"]};
                color: {theme["secondary_text"]};
            }}

            QProgressBar#miniProgressBar {{
                background: {theme["surface_alt"]};
                border: none;
                border-radius: 2px;
            }}

            QProgressBar#miniProgressBar::chunk {{
                background: {accent};
                border-radius: 2px;
            }}

            QPushButton#miniSkipButton {{
                color: {theme["text"]};
                background: transparent;
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 5px;
                font-size: 11px;
                font-weight: 600;
            }}

            QPushButton#miniSkipButton:hover {{
                background: {theme["surface_alt"]};
            }}

            QPushButton#miniOpenButton {{
                color: {theme["text"]};
                background: transparent;
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 5px;
                font-size: 11px;
                font-weight: 600;
            }}

            QPushButton#miniOpenButton:hover {{
                background: {theme["surface_alt"]};
            }}
            """
