from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.themes import THEMES, get_theme
from app.services.theme_service import resolve as resolve_theme


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings,
        sound_manager,
        parent=None,
        goal_service=None,
    ):
        super().__init__(parent)

        self.settings = settings
        self.sound_manager = sound_manager
        self.goal_service = goal_service

        self.selected_accent = (
            settings.get_accent_color()
        )

        self.selected_background = (
            settings.get_background_color()
        )

        self.selected_custom_sound = (
            settings.get_custom_sound()
        )

        self.setWindowTitle(
            "Focus Flow Settings"
        )

        self.setMinimumSize(
            520,
            560,
        )

        self.resize(
            560,
            720,
        )

        self.build_ui()
        self.apply_theme()

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):
        outer_layout = QVBoxLayout(self)

        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        outer_layout.setSpacing(0)

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------

        header = QFrame()
        header.setObjectName(
            "settingsHeader"
        )

        header_layout = QVBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            28,
            24,
            28,
            22,
        )

        header_layout.setSpacing(5)

        title = QLabel("Settings")
        title.setObjectName(
            "settingsTitle"
        )

        subtitle = QLabel(
            "Customize your focus experience."
        )

        subtitle.setObjectName(
            "settingsSubtitle"
        )

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        outer_layout.addWidget(header)

        # -----------------------------------------------------
        # Scroll
        # -----------------------------------------------------

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )

        content_layout.setContentsMargins(
            28,
            24,
            28,
            28,
        )

        content_layout.setSpacing(18)

        # =====================================================
        # TIMER
        # =====================================================

        timer_section = self.create_section(
            "Timer",
            "Set how long you want to work and rest.",
        )

        timer_layout = timer_section.layout()

        self.focus_spin = (
            self.create_spinbox(
                self.settings.get_focus_minutes(),
                1,
                180,
                " min",
            )
        )

        self.short_break_spin = (
            self.create_spinbox(
                self.settings.get_short_break_minutes(),
                1,
                60,
                " min",
            )
        )

        self.long_break_spin = (
            self.create_spinbox(
                self.settings.get_long_break_minutes(),
                1,
                120,
                " min",
            )
        )

        self.sessions_spin = (
            self.create_spinbox(
                self.settings.get_sessions_before_long_break(),
                1,
                12,
                " sessions",
            )
        )

        timer_layout.addWidget(
            self.create_setting_row(
                "Focus duration",
                "Length of each focus session.",
                self.focus_spin,
            )
        )

        timer_layout.addWidget(
            self.create_setting_row(
                "Short break",
                "Break after a normal focus session.",
                self.short_break_spin,
            )
        )

        timer_layout.addWidget(
            self.create_setting_row(
                "Long break",
                "Longer recovery break after a cycle.",
                self.long_break_spin,
            )
        )

        timer_layout.addWidget(
            self.create_setting_row(
                "Sessions before long break",
                "Number of focus sessions in one cycle.",
                self.sessions_spin,
            )
        )

        content_layout.addWidget(
            timer_section
        )

        # =====================================================
        # GOAL
        # =====================================================

        goal_section = self.create_section(
            "Daily Goal",
            "Set a target for your total daily focus time.",
        )

        goal_layout = goal_section.layout()

        self.goal_spin = (
            self.create_spinbox(
                self._current_goal_minutes(),
                15,
                1440,
                " min",
            )
        )

        goal_layout.addWidget(
            self.create_setting_row(
                "Daily focus goal",
                "Your target amount of focused work each day.",
                self.goal_spin,
            )
        )

        content_layout.addWidget(
            goal_section
        )

        # =====================================================
        # APPEARANCE
        # =====================================================

        appearance_section = self.create_section(
            "Appearance",
            "Choose a design or personalize its colors.",
        )

        appearance_layout = (
            appearance_section.layout()
        )

        self.theme_combo = QComboBox()

        self.theme_combo.addItems(
            ["System", *THEMES.keys()]
        )

        self.theme_combo.setCurrentText(
            self.settings.get_theme()
        )

        appearance_layout.addWidget(
            self.create_setting_row(
                "Design",
                "Choose one of the Focus Flow designs.",
                self.theme_combo,
            )
        )

        # -----------------------------------------------------
        # Accent
        # -----------------------------------------------------

        accent_row = QHBoxLayout()
        accent_row.setSpacing(12)

        accent_text = QVBoxLayout()
        accent_text.setSpacing(2)

        accent_title = QLabel(
            "Accent color"
        )

        accent_title.setObjectName(
            "settingTitle"
        )

        accent_description = QLabel(
            "Color used for buttons and highlights."
        )

        accent_description.setObjectName(
            "settingDescription"
        )

        accent_text.addWidget(
            accent_title
        )

        accent_text.addWidget(
            accent_description
        )

        self.accent_button = QPushButton()

        self.accent_button.setFixedSize(
            100,
            38,
        )

        self.accent_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.update_color_button(
            self.accent_button,
            self.selected_accent,
        )

        accent_row.addLayout(
            accent_text
        )

        accent_row.addStretch()

        accent_row.addWidget(
            self.accent_button
        )

        appearance_layout.addLayout(
            accent_row
        )

        self.accent_button.clicked.connect(
            self.choose_accent
        )

        # -----------------------------------------------------
        # Background
        # -----------------------------------------------------

        background_row = QHBoxLayout()
        background_row.setSpacing(12)

        background_text = QVBoxLayout()
        background_text.setSpacing(2)

        background_title = QLabel(
            "Background color"
        )

        background_title.setObjectName(
            "settingTitle"
        )

        background_description = QLabel(
            "Override the selected design's background."
        )

        background_description.setObjectName(
            "settingDescription"
        )

        background_text.addWidget(
            background_title
        )

        background_text.addWidget(
            background_description
        )

        self.background_button = QPushButton()

        self.background_button.setFixedSize(
            100,
            38,
        )

        self.background_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.update_color_button(
            self.background_button,
            self.selected_background,
        )

        background_row.addLayout(
            background_text
        )

        background_row.addStretch()

        background_row.addWidget(
            self.background_button
        )

        appearance_layout.addLayout(
            background_row
        )

        self.background_button.clicked.connect(
            self.choose_background
        )

        reset_colors_button = QPushButton(
            "Use Design Colors"
        )

        reset_colors_button.setObjectName(
            "secondaryAction"
        )

        reset_colors_button.clicked.connect(
            self.reset_colors
        )

        appearance_layout.addWidget(
            reset_colors_button
        )

        self.theme_combo.currentTextChanged.connect(
            self.theme_preview_changed
        )

        content_layout.addWidget(
            appearance_section
        )

        # =====================================================
        # SOUND
        # =====================================================

        sound_section = self.create_section(
            "Sound",
            "Choose what Focus Flow plays when a timer finishes.",
        )

        sound_layout = sound_section.layout()

        self.sound_combo = QComboBox()

        self.sound_combo.addItems(
            [
                "System Bell",
                "Double Bell",
                "Custom WAV",
            ]
        )

        self.sound_combo.setCurrentText(
            self.settings.get_sound()
        )

        sound_layout.addWidget(
            self.create_setting_row(
                "Notification",
                "Sound played when a session ends.",
                self.sound_combo,
            )
        )

        sound_buttons = QHBoxLayout()
        sound_buttons.setSpacing(10)

        self.choose_sound_button = QPushButton(
            "Choose WAV File"
        )

        self.test_sound_button = QPushButton(
            "Test Sound"
        )

        self.choose_sound_button.setObjectName(
            "secondaryAction"
        )

        self.test_sound_button.setObjectName(
            "secondaryAction"
        )

        sound_buttons.addWidget(
            self.choose_sound_button
        )

        sound_buttons.addWidget(
            self.test_sound_button
        )

        sound_layout.addLayout(
            sound_buttons
        )

        self.custom_sound_label = QLabel()

        self.custom_sound_label.setObjectName(
            "fileLabel"
        )

        self.update_custom_sound_label()

        sound_layout.addWidget(
            self.custom_sound_label
        )

        self.choose_sound_button.clicked.connect(
            self.choose_sound
        )

        self.test_sound_button.clicked.connect(
            self.test_sound
        )

        content_layout.addWidget(
            sound_section
        )

        # =====================================================
        # NOTIFICATIONS
        # =====================================================

        notifications_section = self.create_section(
            "Notifications",
            "Control desktop notifications when sessions finish.",
        )

        notifications_layout = (
            notifications_section.layout()
        )

        self.notifications_combo = QComboBox()

        self.notifications_combo.addItems(
            [
                "Enabled",
                "Disabled",
            ]
        )

        current_notification = (
            "Enabled"
            if self.settings.get_notifications_enabled()
            else "Disabled"
        )

        self.notifications_combo.setCurrentText(
            current_notification
        )

        notifications_layout.addWidget(
            self.create_setting_row(
                "Desktop notifications",
                "Show a macOS notification when a timer finishes.",
                self.notifications_combo,
            )
        )

        content_layout.addWidget(
            notifications_section
        )

        # =====================================================
        # COMPACT TIMER (Group 4)
        # =====================================================

        mini_section = self.create_section(
            "Compact Timer",
            "Control the always-on-top mini window.",
        )

        mini_layout = mini_section.layout()

        self.opacity_spin = self.create_spinbox(
            int(round(self.settings.get_mini_opacity() * 100)),
            40,
            100,
            " %",
        )

        mini_layout.addWidget(
            self.create_setting_row(
                "Mini window opacity",
                "Transparency of the compact timer overlay.",
                self.opacity_spin,
            )
        )

        content_layout.addWidget(mini_section)

        # -----------------------------------------------------
        # Bottom spacing
        # -----------------------------------------------------

        content_layout.addStretch()

        scroll.setWidget(content)

        outer_layout.addWidget(
            scroll,
            1,
        )

        # =====================================================
        # Footer
        # =====================================================

        footer = QFrame()

        footer.setObjectName(
            "settingsFooter"
        )

        footer_layout = QHBoxLayout(
            footer
        )

        footer_layout.setContentsMargins(
            28,
            16,
            28,
            16,
        )

        footer_layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setObjectName(
            "saveButton"
        )

        buttons.accepted.connect(
            self.accept
        )

        buttons.rejected.connect(
            self.reject
        )

        footer_layout.addWidget(
            buttons
        )

        outer_layout.addWidget(
            footer
        )

    # =========================================================
    # Helpers
    # =========================================================

    def create_section(
        self,
        title,
        description,
    ):
        section = QFrame()

        section.setObjectName(
            "settingsSection"
        )

        layout = QVBoxLayout(
            section
        )

        layout.setContentsMargins(
            20,
            18,
            20,
            20,
        )

        layout.setSpacing(16)

        title_label = QLabel(title)

        title_label.setObjectName(
            "sectionTitle"
        )

        description_label = QLabel(
            description
        )

        description_label.setObjectName(
            "sectionDescription"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            description_label
        )

        return section

    def create_setting_row(
        self,
        title,
        description,
        widget,
    ):
        row = QHBoxLayout()

        row.setSpacing(15)

        text_layout = QVBoxLayout()

        text_layout.setSpacing(2)

        title_label = QLabel(title)

        title_label.setObjectName(
            "settingTitle"
        )

        description_label = QLabel(
            description
        )

        description_label.setObjectName(
            "settingDescription"
        )

        description_label.setWordWrap(
            True
        )

        text_layout.addWidget(
            title_label
        )

        text_layout.addWidget(
            description_label
        )

        row.addLayout(
            text_layout,
            1,
        )

        widget.setMinimumWidth(
            135
        )

        row.addWidget(widget)

        container = QWidget()

        container.setLayout(row)

        return container

    def create_spinbox(
        self,
        value,
        minimum,
        maximum,
        suffix,
    ):
        spin = QSpinBox()

        spin.setRange(
            minimum,
            maximum,
        )

        spin.setValue(value)

        spin.setSuffix(suffix)

        return spin

    # =========================================================
    # Colors
    # =========================================================

    def choose_accent(self):
        initial = QColor(
            self.selected_accent
            or get_theme(
                self.theme_combo.currentText()
            )["accent"]
        )

        color = QColorDialog.getColor(
            initial,
            self,
            "Choose Accent Color",
        )

        if color.isValid():
            self.selected_accent = (
                color.name()
            )

            self.update_color_button(
                self.accent_button,
                self.selected_accent,
            )

    def choose_background(self):
        initial = QColor(
            self.selected_background
            or get_theme(
                self.theme_combo.currentText()
            )["background"]
        )

        color = QColorDialog.getColor(
            initial,
            self,
            "Choose Background Color",
        )

        if color.isValid():
            self.selected_background = (
                color.name()
            )

            self.update_color_button(
                self.background_button,
                self.selected_background,
            )

    def reset_colors(self):
        self.selected_accent = ""
        self.selected_background = ""

        theme = get_theme(
            self.theme_combo.currentText()
        )

        self.update_color_button(
            self.accent_button,
            theme["accent"],
        )

        self.update_color_button(
            self.background_button,
            theme["background"],
        )

    def update_color_button(
        self,
        button,
        color,
    ):
        if not color:
            button.setText("Theme")
            button.setStyleSheet("")
            return

        button.setText(
            color.upper()
        )

        qcolor = QColor(color)

        brightness = (
            qcolor.red() * 299
            + qcolor.green() * 587
            + qcolor.blue() * 114
        ) / 1000

        text_color = (
            "#000000"
            if brightness > 150
            else "#FFFFFF"
        )

        button.setStyleSheet(
            f"""
            QPushButton {{
                background: {color};
                color: {text_color};
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 9px;
                font-size: 11px;
                font-weight: 700;
            }}
            """
        )

    def theme_preview_changed(
        self,
        theme_name,
    ):
        theme = get_theme(
            theme_name
        )

        if not self.selected_accent:
            self.update_color_button(
                self.accent_button,
                theme["accent"],
            )

        if not self.selected_background:
            self.update_color_button(
                self.background_button,
                theme["background"],
            )

        self.apply_theme()

    # =========================================================
    # Sound
    # =========================================================

    def choose_sound(self):
        file_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Choose WAV File",
                "",
                "WAV files (*.wav)",
            )
        )

        if file_path:
            self.selected_custom_sound = (
                file_path
            )

            self.sound_combo.setCurrentText(
                "Custom WAV"
            )

            self.update_custom_sound_label()

    def update_custom_sound_label(self):
        if self.selected_custom_sound:
            path = Path(
                self.selected_custom_sound
            )

            self.custom_sound_label.setText(
                f"Selected: {path.name}"
            )
        else:
            self.custom_sound_label.setText(
                "No custom WAV selected."
            )

    def test_sound(self):
        self.sound_manager.play(
            self.sound_combo.currentText(),
            self.selected_custom_sound,
        )

    # =========================================================
    # Save
    # =========================================================

    def _current_goal_minutes(self):
        if self.goal_service is not None:
            return self.goal_service.get_daily_goal_minutes()
        return self.settings.get_daily_goal_minutes()

    def save_settings(self):
        self.settings.set_focus_minutes(
            self.focus_spin.value()
        )

        self.settings.set_short_break_minutes(
            self.short_break_spin.value()
        )

        self.settings.set_long_break_minutes(
            self.long_break_spin.value()
        )

        self.settings.set_sessions_before_long_break(
            self.sessions_spin.value()
        )

        if self.goal_service is not None:
            self.goal_service.set_daily_goal_minutes(
                self.goal_spin.value()
            )
        else:
            self.settings.set_daily_goal_minutes(
                self.goal_spin.value()
            )

        self.settings.set_theme(
            self.theme_combo.currentText()
        )

        self.settings.set_accent_color(
            self.selected_accent
        )

        self.settings.set_background_color(
            self.selected_background
        )

        self.settings.set_sound(
            self.sound_combo.currentText()
        )

        self.settings.set_custom_sound(
            self.selected_custom_sound
        )

        self.settings.set_notifications_enabled(
            self.notifications_combo.currentText()
            == "Enabled"
        )

        self.settings.set_mini_opacity(
            self.opacity_spin.value() / 100
        )

    # =========================================================
    # Theme
    # =========================================================

    def apply_theme(self):
        resolved = resolve_theme(
            self.theme_combo.currentText()
            if hasattr(
                self,
                "theme_combo",
            )
            else self.settings.get_theme(),
            self.selected_accent,
            self.selected_background,
        )
        theme = resolved["tokens"]

        background = resolved["background"]

        self.setStyleSheet(
            f"""
            QDialog {{
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

            QFrame#settingsHeader {{
                background: {theme["surface"]};
                border-bottom: 1px solid {theme["border"]};
            }}

            QLabel#settingsTitle {{
                font-size: 26px;
                font-weight: 700;
            }}

            QLabel#settingsSubtitle {{
                color: {theme["secondary_text"]};
                font-size: 13px;
            }}

            QFrame#settingsSection {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 16px;
            }}

            QLabel#sectionTitle {{
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#sectionDescription {{
                color: {theme["secondary_text"]};
                font-size: 12px;
            }}

            QLabel#settingTitle {{
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#settingDescription {{
                color: {theme["secondary_text"]};
                font-size: 11px;
            }}

            QLabel#fileLabel {{
                color: {theme["secondary_text"]};
                font-size: 11px;
            }}

            QSpinBox,
            QComboBox {{
                background: {theme["input"]};
                color: {theme["input_text"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 8px 10px;
                min-height: 18px;
            }}

            QSpinBox:focus,
            QComboBox:focus {{
                border: 2px solid {theme["accent"]};
            }}

            QComboBox QAbstractItemView {{
                background: {theme["surface"]};
                color: {theme["text"]};
                selection-background-color:
                    {theme["accent"]};
                selection-color:
                    {theme["button_text"]};
            }}

            QPushButton#secondaryAction {{
                background: {theme["surface_alt"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 9px 14px;
                font-weight: 600;
            }}

            QPushButton#secondaryAction:hover {{
                background: {theme["border"]};
            }}

            QPushButton#saveButton {{
                background: {theme["accent"]};
                color: {theme["button_text"]};
                border: none;
                border-radius: 9px;
                padding: 9px 20px;
                min-width: 80px;
                font-weight: 700;
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 9px;
                margin: 4px;
            }}

            QScrollBar::handle:vertical {{
                background: {theme["border"]};
                border-radius: 4px;
                min-height: 35px;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QFrame#settingsFooter {{
                background: {theme["surface"]};
                border-top: 1px solid {theme["border"]};
            }}
            """
        )
