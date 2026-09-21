from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QSize, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.database import Database, DatabaseError
from app.floating_timer import FloatingTimer
from app.goals import GoalManager
from app.history import HistoryManager
from app.history_dialog import HistoryDialog
from app.menu_bar import MenuBarManager
from app.notifications import NotificationManager
from app.settings import AppSettings
from app.shortcuts import ShortcutManager
from app.sounds import SoundManager
from app.themes import THEMES, get_theme
from app.timer import PomodoroTimer


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings,
        sound_manager,
        parent=None,
    ):
        super().__init__(parent)

        self.settings = settings
        self.sound_manager = sound_manager

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
                self.settings.get_daily_goal_minutes(),
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
            THEMES.keys()
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

    # =========================================================
    # Theme
    # =========================================================

    def apply_theme(self):
        theme = get_theme(
            self.theme_combo.currentText()
            if hasattr(
                self,
                "theme_combo",
            )
            else self.settings.get_theme()
        )

        background = (
            self.selected_background
            or theme["background"]
        )

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # =====================================================
        # Core services
        # =====================================================

        self.settings = AppSettings()

        self.timer = PomodoroTimer()

        self.sound_manager = SoundManager(self)

        self.database = Database()

        self.history = HistoryManager(
            self.database
        )

        self.goals = GoalManager(
            self.database
        )

        self.notifications = (
            NotificationManager()
        )

        # =====================================================
        # Timer state
        # =====================================================

        self.mode = "Focus"

        self.session_number = 1

        self.current_task = ""

        self.focus_start_time = None

        # =====================================================
        # Window
        # =====================================================

        self.setWindowTitle(
            "Focus Flow"
        )

        self.setMinimumSize(
            560,
            700,
        )

        self.resize(
            620,
            800,
        )

        # =====================================================
        # Build application
        # =====================================================

        self.build_ui()

        self.connect_signals()

        self.load_initial_timer()

        self.apply_theme()

        self.update_buttons()

        # =====================================================
        # Additional controllers
        # =====================================================

        self.floating_timer = (
            FloatingTimer(
                self.timer,
                toggle_callback=self.toggle_timer,
            )
        )

        self.floating_timer.close_requested.connect(
            self.hide_floating_timer
        )

        self.apply_theme()

        self.shortcut_manager = (
            ShortcutManager(self)
        )

        self.menu_bar_manager = (
            MenuBarManager(self)
        )

        # The compact timer is an overlay shown only while Focus Flow is
        # inactive; it starts hidden while the main window has focus.
        self.hide_floating_timer()

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):
        central = QWidget()

        self.setCentralWidget(
            central
        )

        self.main_layout = QVBoxLayout(
            central
        )

        self.main_layout.setContentsMargins(
            42,
            34,
            42,
            32,
        )

        self.main_layout.setSpacing(
            18
        )

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------

        header = QHBoxLayout()

        title_container = QVBoxLayout()

        title_container.setSpacing(2)

        title = QLabel(
            "Focus Flow"
        )

        title.setObjectName(
            "appTitle"
        )

        subtitle = QLabel(
            "Focus deeply. Rest intentionally."
        )

        subtitle.setObjectName(
            "appSubtitle"
        )

        title_container.addWidget(
            title
        )

        title_container.addWidget(
            subtitle
        )

        header.addLayout(
            title_container
        )

        header.addStretch()

        self.history_button = QPushButton("History")
        self.history_button.setObjectName("secondaryButton")
        self.history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self.history_button)

        # -----------------------------------------------------
        # Settings
        # -----------------------------------------------------

        self.settings_button = QPushButton()

        self.settings_button.setObjectName(
            "settingsButton"
        )

        icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "icons"
            / "settings.svg"
        )

        self.settings_button.setIcon(
            QIcon(str(icon_path))
        )

        self.settings_button.setIconSize(
            QSize(20, 20)
        )

        self.settings_button.setFixedSize(
            42,
            42,
        )

        self.settings_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        header.addWidget(
            self.settings_button
        )

        self.main_layout.addLayout(
            header
        )

        # -----------------------------------------------------
        # Task input
        # -----------------------------------------------------

        task_label = QLabel(
            "What are you focusing on?"
        )

        task_label.setObjectName(
            "taskLabel"
        )

        self.main_layout.addWidget(
            task_label
        )

        self.task_input = QLineEdit()

        self.task_input.setPlaceholderText(
            "e.g. Build Focus Flow"
        )

        self.task_input.setObjectName(
            "taskInput"
        )

        self.main_layout.addWidget(
            self.task_input
        )

        # -----------------------------------------------------
        # Mode
        # -----------------------------------------------------

        self.mode_label = QLabel(
            "FOCUS SESSION"
        )

        self.mode_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.mode_label.setObjectName(
            "modeLabel"
        )

        self.main_layout.addSpacing(
            8
        )

        self.main_layout.addWidget(
            self.mode_label
        )

        # -----------------------------------------------------
        # Timer card
        # -----------------------------------------------------

        self.timer_card = QFrame()

        self.timer_card.setObjectName(
            "timerCard"
        )

        card_layout = QVBoxLayout(
            self.timer_card
        )

        card_layout.setContentsMargins(
            30,
            48,
            30,
            42,
        )

        card_layout.setSpacing(
            12
        )

        self.time_label = QLabel(
            "25:00"
        )

        self.time_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.time_label.setObjectName(
            "timeLabel"
        )

        card_layout.addWidget(
            self.time_label
        )

        self.session_label = QLabel(
            "Session 1 of 4"
        )

        self.session_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.session_label.setObjectName(
            "sessionLabel"
        )

        card_layout.addWidget(
            self.session_label
        )

        self.main_layout.addWidget(
            self.timer_card
        )

        # -----------------------------------------------------
        # Progress
        # -----------------------------------------------------

        self.progress = QProgressBar()

        self.progress.setObjectName(
            "progressBar"
        )

        self.progress.setTextVisible(
            False
        )

        self.progress.setFixedHeight(
            7
        )

        self.main_layout.addWidget(
            self.progress
        )

        # -----------------------------------------------------
        # Session dots
        # -----------------------------------------------------

        dots_layout = QHBoxLayout()

        dots_layout.setSpacing(
            8
        )

        dots_layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.session_dots = []

        for _ in range(12):
            dot = QFrame()

            dot.setFixedSize(
                9,
                9,
            )

            dot.setObjectName(
                "sessionDot"
            )

            dots_layout.addWidget(
                dot
            )

            self.session_dots.append(
                dot
            )

        self.main_layout.addLayout(
            dots_layout
        )

        # -----------------------------------------------------
        # Daily goal
        # -----------------------------------------------------

        self.goal_label = QLabel()

        self.goal_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.goal_label.setObjectName(
            "goalLabel"
        )

        self.main_layout.addWidget(
            self.goal_label
        )

        self.main_layout.addStretch()

        # -----------------------------------------------------
        # Controls
        # -----------------------------------------------------

        controls = QHBoxLayout()

        controls.setSpacing(
            10
        )

        self.reset_button = QPushButton(
            "Reset"
        )

        self.pause_button = QPushButton(
            "Pause"
        )

        self.start_button = QPushButton(
            "Start"
        )

        self.reset_button.setObjectName(
            "secondaryButton"
        )

        self.pause_button.setObjectName(
            "secondaryButton"
        )

        self.start_button.setObjectName(
            "primaryButton"
        )

        for button in (
            self.reset_button,
            self.pause_button,
            self.start_button,
        ):
            button.setMinimumHeight(
                46
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

        controls.addWidget(
            self.reset_button
        )

        controls.addWidget(
            self.pause_button
        )

        controls.addWidget(
            self.start_button
        )

        self.main_layout.addLayout(
            controls
        )

        # -----------------------------------------------------
        # Footer
        # -----------------------------------------------------

        self.footer_label = QLabel()

        self.footer_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.footer_label.setObjectName(
            "footerLabel"
        )

        self.main_layout.addWidget(
            self.footer_label
        )

    # =========================================================
    # Signals
    # =========================================================

    def connect_signals(self):
        self.start_button.clicked.connect(
            self.start_timer
        )

        self.pause_button.clicked.connect(
            self.pause_timer
        )

        self.reset_button.clicked.connect(
            self.reset_timer
        )

        self.settings_button.clicked.connect(
            self.open_settings
        )

        self.history_button.clicked.connect(
            self.open_history
        )

        self.timer.tick.connect(
            self.update_display
        )

        self.timer.finished.connect(
            self.timer_finished
        )

    # =========================================================
    # Initial timer
    # =========================================================

    def load_initial_timer(self):
        self.mode = "Focus"

        self.session_number = 1

        self.current_task = ""

        self.focus_start_time = None

        self.set_mode(
            "Focus"
        )

        minutes = (
            self.settings.get_focus_minutes()
        )

        self.timer.reset(
            minutes * 60
        )

        self.update_display(
            self.timer.remaining_seconds
        )

        self.update_goal_display()

    # =========================================================
    # Timer controls
    # =========================================================

    def start_timer(self):
        if self.mode == "Focus":
            if not self.current_task:
                task = (
                    self.task_input.text()
                    .strip()
                )

                if not task:
                    QMessageBox.warning(
                        self,
                        "Focus task required",
                        "Please enter what you want to focus on before starting.",
                    )

                    self.task_input.setFocus()

                    return

                self.current_task = task

                if hasattr(self, "floating_timer"):
                    self.floating_timer.set_task_name(task)

                self.focus_start_time = (
                    datetime.now()
                )

            self.task_input.setEnabled(
                False
            )

        self.timer.start()

        self.update_buttons()

    def pause_timer(self):
        self.timer.pause()

        self.update_buttons()

    def toggle_timer(self):
        if self.timer.is_running():
            self.pause_timer()
        else:
            self.start_timer()

    def reset_timer(self):
        self.timer.pause()

        self.current_task = ""

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_task_name("")

        self.focus_start_time = None

        self.task_input.setEnabled(
            True
        )

        self.task_input.clear()

        if self.mode == "Focus":
            minutes = (
                self.settings.get_focus_minutes()
            )

        elif self.mode == "Short Break":
            minutes = (
                self.settings.get_short_break_minutes()
            )

        else:
            minutes = (
                self.settings.get_long_break_minutes()
            )

        self.timer.reset(
            minutes * 60
        )

        self.update_display(
            self.timer.remaining_seconds
        )

        self.update_buttons()

    # =========================================================
    # Display
    # =========================================================

    def update_display(self, seconds):
        minutes = seconds // 60

        remaining_seconds = seconds % 60

        self.time_label.setText(
            f"{minutes:02d}:{remaining_seconds:02d}"
        )

        if self.timer.total_seconds > 0:
            elapsed = (
                self.timer.total_seconds
                - seconds
            )

            self.progress.setValue(
                int(
                    elapsed
                    / self.timer.total_seconds
                    * 100
                )
            )

        self.update_buttons()

    def update_buttons(self):
        running = (
            self.timer.is_running()
        )

        self.start_button.setEnabled(
            not running
        )

        self.pause_button.setEnabled(
            running
        )

        if hasattr(self, "floating_timer"):
            self.floating_timer.update_pause_button()

    # =========================================================
    # Timer finished
    # =========================================================

    def timer_finished(self):
        self.sound_manager.play(
            self.settings.get_sound(),
            self.settings.get_custom_sound(),
        )

        if self.mode == "Focus":
            self.save_completed_focus_session()

            if self.settings.get_notifications_enabled():
                self.notifications.focus_complete()

            break_type = self.next_break_type()
            self.prepare_break(break_type)
            self.show_break_dialog(break_type)

        elif self.mode == "Short Break":
            if self.settings.get_notifications_enabled():
                self.notifications.short_break_complete()

            self.prepare_focus_session()
            self.show_focus_dialog()

        else:
            if self.settings.get_notifications_enabled():
                self.notifications.long_break_complete()

            self.prepare_focus_session()
            self.show_focus_dialog()

    # =========================================================
    # History
    # =========================================================

    def save_completed_focus_session(self):
        if not self.current_task:
            return

        duration_seconds = (
            self.timer.total_seconds
        )

        start_time = (
            self.focus_start_time
            or datetime.now()
        )

        try:
            self.history.add_focus_session(
                task=self.current_task,
                start_time=start_time.isoformat(
                    timespec="seconds"
                ),
                duration_seconds=duration_seconds,
            )
        except DatabaseError as error:
            QMessageBox.warning(
                self,
                "Focus session was not saved",
                "The timer will continue, but this completed session could "
                f"not be saved.\n\n{error}",
            )

        self.current_task = ""

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_task_name("")

        self.focus_start_time = None

        self.task_input.setEnabled(
            True
        )

        self.task_input.clear()

        self.update_goal_display()

    # =========================================================
    # Break dialogs
    # =========================================================

    def next_break_type(self):
        sessions = self.settings.get_sessions_before_long_break()
        return "long" if self.session_number >= sessions else "short"

    def show_break_dialog(self, break_type):
        break_text = (
            "You've completed a full focus cycle."
            if break_type == "long"
            else "Your focus session is complete."
        )

        box = QMessageBox(self)

        box.setWindowTitle(
            "Focus session complete"
        )

        box.setText(
            break_text
        )

        if break_type == "long":
            informative = (
                "Would you like to start your long break?"
            )

            button_text = (
                "Start Long Break"
            )

        else:
            informative = (
                "Would you like to start your short break?"
            )

            button_text = (
                "Start Short Break"
            )

        box.setInformativeText(
            informative
        )

        start_button = box.addButton(
            button_text,
            QMessageBox.ButtonRole.AcceptRole,
        )

        box.addButton(
            "Later",
            QMessageBox.ButtonRole.RejectRole,
        )

        box.exec()

        if (
            box.clickedButton()
            == start_button
        ):
            self.start_timer()

    def show_focus_dialog(self):
        box = QMessageBox(self)

        box.setWindowTitle(
            "Break complete"
        )

        box.setText(
            "Your break is finished."
        )

        box.setInformativeText(
            "Ready for another focus session?"
        )

        start_button = box.addButton(
            "Start Focus",
            QMessageBox.ButtonRole.AcceptRole,
        )

        box.addButton(
            "Later",
            QMessageBox.ButtonRole.RejectRole,
        )

        box.exec()

        if (
            box.clickedButton()
            == start_button
        ):
            # Focus mode is already prepared. The user chooses a task and
            # explicitly presses Start when ready.
            self.task_input.setFocus()

    # =========================================================
    # Pomodoro cycle
    # =========================================================

    def start_short_break(self):
        self.prepare_break("short")
        self.timer.start()
        self.update_buttons()

    def start_long_break(self):
        self.prepare_break("long")
        self.timer.start()
        self.update_buttons()

    def start_focus(self):
        """Prepare a new focus session; starting requires an explicit click."""
        self.prepare_focus_session()

    def prepare_break(self, break_type):
        if break_type == "long":
            self.set_mode("Long Break")
            minutes = self.settings.get_long_break_minutes()
        else:
            self.set_mode("Short Break")
            minutes = self.settings.get_short_break_minutes()

        self.timer.reset(minutes * 60)
        self.update_buttons()

    def prepare_focus_session(self):
        sessions = (
            self.settings
            .get_sessions_before_long_break()
        )

        if self.session_number >= sessions:
            self.session_number = 1
        else:
            self.session_number += 1

        self.set_mode("Focus")

        minutes = (
            self.settings
            .get_focus_minutes()
        )

        self.timer.reset(minutes * 60)

        self.current_task = ""

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_task_name("")

        self.focus_start_time = None
        self.task_input.setEnabled(True)
        self.task_input.clear()

        self.task_input.setFocus()

        self.update_buttons()


    # =========================================================
    # Mode
    # =========================================================

    def set_mode(self, mode):
        self.mode = mode

        if mode == "Focus":
            self.mode_label.setText(
                "FOCUS SESSION"
            )

        elif mode == "Short Break":
            self.mode_label.setText(
                "SHORT BREAK"
            )

        else:
            self.mode_label.setText(
                "LONG BREAK"
            )

        if hasattr(self, "floating_timer"):
            self.floating_timer.set_mode(mode)

        self.update_session_information()

    def update_session_information(self):
        total_sessions = (
            self.settings
            .get_sessions_before_long_break()
        )

        if self.mode == "Focus":
            self.session_label.setText(
                f"Session {self.session_number} "
                f"of {total_sessions}"
            )

        elif self.mode == "Short Break":
            self.session_label.setText(
                "Short recovery"
            )

        else:
            self.session_label.setText(
                "Full cycle recovery"
            )

        self.update_session_dots()

        self.update_footer()

    def update_session_dots(self):
        total = min(
            len(self.session_dots),
            self.settings
            .get_sessions_before_long_break(),
        )

        for index, dot in enumerate(
            self.session_dots
        ):
            if index >= total:
                dot.hide()
                continue

            dot.show()

            if (
                self.mode == "Focus"
                and index + 1 == self.session_number
            ):
                dot.setProperty(
                    "active",
                    True,
                )

            elif (
                self.mode != "Focus"
                and index + 1 <= self.session_number
            ):
                dot.setProperty(
                    "active",
                    True,
                )

            else:
                dot.setProperty(
                    "active",
                    False,
                )

            dot.style().unpolish(dot)
            dot.style().polish(dot)

    # =========================================================
    # Goal
    # =========================================================

    def update_goal_display(self):
        if not self.database.is_available:
            self.goal_label.setText(
                "Session history is unavailable. Check the application data folder."
            )
            self.goal_label.setToolTip(self.database.error_message)
            return

        self.goal_label.setToolTip("")
        total_seconds = (
            self.history.get_today_total()
        )

        total_minutes = (
            total_seconds // 60
        )

        goal_minutes = (
            self.settings
            .get_daily_goal_minutes()
        )

        if total_minutes >= goal_minutes:
            self.goal_label.setText(
                f"Daily goal complete • "
                f"{total_minutes} / {goal_minutes} min"
            )

        else:
            self.goal_label.setText(
                f"Today: "
                f"{total_minutes} / "
                f"{goal_minutes} min focused"
            )

    # =========================================================
    # Footer
    # =========================================================

    def update_footer(self):
        focus = (
            self.settings
            .get_focus_minutes()
        )

        short_break = (
            self.settings
            .get_short_break_minutes()
        )

        long_break = (
            self.settings
            .get_long_break_minutes()
        )

        self.footer_label.setText(
            f"{focus} min focus  •  "
            f"{short_break} min short break  •  "
            f"{long_break} min long break"
        )

    # =========================================================
    # History
    # =========================================================

    def open_history(self):
        dialog = HistoryDialog(
            self.history,
            self.settings,
            self,
        )
        dialog.exec()

    # =========================================================
    # Settings
    # =========================================================

    def open_settings(self):
        dialog = SettingsDialog(
            self.settings,
            self.sound_manager,
            self,
        )

        if (
            dialog.exec()
            == QDialog.DialogCode.Accepted
        ):
            dialog.save_settings()

            self.apply_theme()

            self.update_session_information()

            self.update_goal_display()

            if not self.timer.is_running():
                self.reset_timer()

    # =========================================================
    # Floating timer
    # =========================================================

    def show_floating_timer(self):
        self.floating_timer.set_mode(
            self.mode
        )

        self.floating_timer.update_time(
            self.timer.remaining_seconds
        )

        self.floating_timer.show()

        self.floating_timer.raise_()

    def hide_floating_timer(self):
        self.floating_timer.hide()

    def event(self, event):
        result = super().event(event)
        if event.type() in (
            QEvent.Type.WindowActivate,
            QEvent.Type.WindowDeactivate,
        ):
            # Qt updates application/window activation after this event has
            # been delivered, so defer a single event-loop turn without
            # polling continuously.
            QTimer.singleShot(0, self.sync_floating_timer_visibility)
        return result

    def sync_floating_timer_visibility(self, app_is_active=None):
        """Show the overlay only after Focus Flow loses application focus."""
        if app_is_active is None:
            app = QApplication.instance()
            app_is_active = (
                app is not None
                and app.applicationState()
                == Qt.ApplicationState.ApplicationActive
            )

        if self.isActiveWindow() or app_is_active:
            self.hide_floating_timer()
        else:
            self.show_floating_timer()

    # =========================================================
    # Application
    # =========================================================

    def close_application(self):
        self.floating_timer.close()

        self.database.close()

        self.close()

    def closeEvent(self, event):
        self.database.close()

        event.accept()

    # =========================================================
    # Theme
    # =========================================================

    def apply_theme(self):
        theme = get_theme(
            self.settings.get_theme()
        )

        background = (
            self.settings.get_background_color()
            or theme["background"]
        )

        accent = (
            self.settings.get_accent_color()
            or theme["accent"]
        )

        if hasattr(self, "floating_timer"):
            self.floating_timer.apply_theme(theme, accent)

        self.setStyleSheet(
            f"""
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
        )

        self.update_session_dots()
