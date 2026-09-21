from PySide6.QtCore import QObject, QSettings, Signal

from app.themes import THEMES

#: Theme name that follows the macOS system appearance (Group 4).
#: Stored like any other theme; resolved to a concrete palette by
#: ``theme_service.resolve``.
SYSTEM_THEME_NAME = "System"

VALID_SOUNDS = (
    "System Bell",
    "Double Bell",
    "Custom WAV",
)


def _clamp_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


class SettingsStore(QObject):
    """Typed, validated wrapper around QSettings (preferences only).

    Daily goals are canonical in the database (see ``app.goals``); this
    store keeps user preferences plus a legacy goal mirror updated by
    ``GoalService``. All reads apply defaults and clamp to valid ranges so
    corrupt settings can never break the timer. All writes validate at
    the boundary and emit ``valueChanged`` when the stored value changes.
    """

    valueChanged = Signal(str)

    def __init__(self, settings=None):
        super().__init__()
        self.settings = (
            settings
            if settings is not None
            else QSettings(
                "Focus Flow",
                "Focus Flow",
            )
        )

    # =====================================================
    # Internal helpers
    # =====================================================

    def _set(self, key, value):
        old = self.settings.value(key, None)
        self.settings.setValue(key, value)
        if old != value:
            self.valueChanged.emit(key)

    # =====================================================
    # Timer
    # =====================================================

    def get_focus_minutes(self):
        return _clamp_int(
            self.settings.value("focus_minutes", 25),
            25, 1, 180,
        )

    def set_focus_minutes(self, value):
        self._set(
            "focus_minutes",
            _clamp_int(value, 25, 1, 180),
        )

    def get_short_break_minutes(self):
        return _clamp_int(
            self.settings.value("short_break_minutes", 5),
            5, 1, 60,
        )

    def set_short_break_minutes(self, value):
        self._set(
            "short_break_minutes",
            _clamp_int(value, 5, 1, 60),
        )

    def get_long_break_minutes(self):
        return _clamp_int(
            self.settings.value("long_break_minutes", 15),
            15, 1, 120,
        )

    def set_long_break_minutes(self, value):
        self._set(
            "long_break_minutes",
            _clamp_int(value, 15, 1, 120),
        )

    def get_sessions_before_long_break(self):
        return _clamp_int(
            self.settings.value("sessions_before_long_break", 4),
            4, 1, 12,
        )

    def set_sessions_before_long_break(self, value):
        self._set(
            "sessions_before_long_break",
            _clamp_int(value, 4, 1, 12),
        )

    # =====================================================
    # Appearance
    # =====================================================

    def get_theme(self):
        name = self.settings.value("theme", "Midnight")
        if name not in THEMES and name != SYSTEM_THEME_NAME:
            return "Midnight"
        return name

    def set_theme(self, value):
        if value not in THEMES and value != SYSTEM_THEME_NAME:
            value = "Midnight"
        self._set("theme", value)

    def get_accent_color(self):
        value = self.settings.value("accent_color", "")
        return value if isinstance(value, str) else ""

    def set_accent_color(self, value):
        self._set(
            "accent_color",
            value if isinstance(value, str) else "",
        )

    def get_background_color(self):
        value = self.settings.value("background_color", "")
        return value if isinstance(value, str) else ""

    def set_background_color(self, value):
        self._set(
            "background_color",
            value if isinstance(value, str) else "",
        )

    # =====================================================
    # Sound
    # =====================================================

    def get_sound(self):
        value = self.settings.value("sound", "System Bell")
        if value not in VALID_SOUNDS:
            return "System Bell"
        return value

    def set_sound(self, value):
        if value not in VALID_SOUNDS:
            value = "System Bell"
        self._set("sound", value)

    def get_custom_sound(self):
        value = self.settings.value("custom_sound", "")
        return value if isinstance(value, str) else ""

    def set_custom_sound(self, value):
        self._set(
            "custom_sound",
            value if isinstance(value, str) else "",
        )

    # =====================================================
    # Notifications
    # =====================================================

    def get_notifications_enabled(self):
        value = self.settings.value(
            "notifications_enabled",
            True,
        )

        if isinstance(value, bool):
            return value

        return str(value).lower() in (
            "true",
            "1",
            "yes",
        )

    def set_notifications_enabled(self, value):
        self._set(
            "notifications_enabled",
            bool(value),
        )

    # =====================================================
    # Mini/floating window position (restored on future use;
    # None when never saved or corrupt)
    # =====================================================

    def get_mini_position(self):
        raw_x = self.settings.value("mini_pos_x", None)
        raw_y = self.settings.value("mini_pos_y", None)
        try:
            x = int(raw_x)
            y = int(raw_y)
        except (TypeError, ValueError):
            return None
        if abs(x) > 10000 or abs(y) > 10000:
            return None
        return (x, y)

    def set_mini_position(self, x, y):
        try:
            x = int(x)
            y = int(y)
        except (TypeError, ValueError):
            return
        if abs(x) > 10000 or abs(y) > 10000:
            return
        self._set("mini_pos_x", x)
        self._set("mini_pos_y", y)

    # =====================================================
    # Mini/floating window opacity (Group 4; 0.4–1.0, default 1.0)
    # =====================================================

    def get_mini_opacity(self):
        try:
            value = float(self.settings.value("mini_opacity", 1.0))
        except (TypeError, ValueError):
            return 1.0
        return max(0.4, min(1.0, value))

    def set_mini_opacity(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self._set("mini_opacity", max(0.4, min(1.0, value)))

    # =====================================================
    # Daily goal (legacy preferences mirror; Group 2 made the
    # database the canonical store — see app.goals.GoalManager
    # and app.services.goal_service.GoalService. Kept in sync
    # on every GoalService write for backward compatibility.)
    # =====================================================

    def get_daily_goal_minutes(self):
        return _clamp_int(
            self.settings.value("daily_goal_minutes", 120),
            120, 15, 1440,
        )

    def set_daily_goal_minutes(self, value):
        self._set(
            "daily_goal_minutes",
            _clamp_int(value, 120, 15, 1440),
        )
