from PySide6.QtCore import QSettings


class AppSettings:
    def __init__(self):
        self.settings = QSettings("Focus Flow", "Focus Flow")

    # -------------------------
    # Timer
    # -------------------------

    def get_focus_minutes(self):
        return int(self.settings.value("focus_minutes", 25))

    def set_focus_minutes(self, value):
        self.settings.setValue("focus_minutes", value)

    def get_short_break_minutes(self):
        return int(self.settings.value("short_break_minutes", 5))

    def set_short_break_minutes(self, value):
        self.settings.setValue("short_break_minutes", value)

    def get_long_break_minutes(self):
        return int(self.settings.value("long_break_minutes", 15))

    def set_long_break_minutes(self, value):
        self.settings.setValue("long_break_minutes", value)

    def get_sessions_before_long_break(self):
        return int(
            self.settings.value(
                "sessions_before_long_break",
                4,
            )
        )

    def set_sessions_before_long_break(self, value):
        self.settings.setValue(
            "sessions_before_long_break",
            value,
        )

    # -------------------------
    # Appearance
    # -------------------------

    def get_theme(self):
        return self.settings.value("theme", "Midnight")

    def set_theme(self, value):
        self.settings.setValue("theme", value)

    def get_accent_color(self):
        return self.settings.value("accent_color", "")

    def set_accent_color(self, value):
        self.settings.setValue("accent_color", value)

    def get_background_color(self):
        return self.settings.value("background_color", "")

    def set_background_color(self, value):
        self.settings.setValue("background_color", value)

    # -------------------------
    # Sound
    # -------------------------

    def get_sound(self):
        return self.settings.value("sound", "System Bell")

    def set_sound(self, value):
        self.settings.setValue("sound", value)

    def get_custom_sound(self):
        return self.settings.value("custom_sound", "")

    def set_custom_sound(self, value):
        self.settings.setValue("custom_sound", value)