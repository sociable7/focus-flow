from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.settings import AppSettings
from app.sounds import SoundManager
from app.themes import THEMES, get_theme
from app.timer import PomodoroTimer


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)

        self.settings = settings

        self.setWindowTitle("Focus Flow Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.focus_spin = QSpinBox()
        self.focus_spin.setRange(1, 180)
        self.focus_spin.setValue(settings.get_focus_minutes())
        self.focus_spin.setSuffix(" min")

        self.short_break_spin = QSpinBox()
        self.short_break_spin.setRange(1, 60)
        self.short_break_spin.setValue(settings.get_short_break_minutes())
        self.short_break_spin.setSuffix(" min")

        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(1, 120)
        self.long_break_spin.setValue(settings.get_long_break_minutes())
        self.long_break_spin.setSuffix(" min")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText(settings.get_theme())

        self.sound_combo = QComboBox()
        self.sound_combo.addItems(
            [
                "System Bell",
                "Double Bell",
                "Custom WAV",
            ]
        )
        self.sound_combo.setCurrentText(settings.get_sound())

        form.addRow("Focus duration:", self.focus_spin)
        form.addRow("Short break:", self.short_break_spin)
        form.addRow("Long break:", self.long_break_spin)
        form.addRow("Theme:", self.theme_combo)
        form.addRow("Sound:", self.sound_combo)

        layout.addLayout(form)

        self.accent_button = QPushButton("Choose Accent Color")
        self.background_button = QPushButton("Choose Background Color")
        self.custom_sound_button = QPushButton("Choose WAV File")

        layout.addWidget(self.accent_button)
        layout.addWidget(self.background_button)
        layout.addWidget(self.custom_sound_button)

        self.accent_button.clicked.connect(self.choose_accent)
        self.background_button.clicked.connect(self.choose_background)
        self.custom_sound_button.clicked.connect(self.choose_sound)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def choose_accent(self):
        color = QColorDialog.getColor()

        if color.isValid():
            self.settings.set_accent_color(color.name())

    def choose_background(self):
        color = QColorDialog.getColor()

        if color.isValid():
            self.settings.set_background_color(color.name())

    def choose_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose WAV File",
            "",
            "WAV files (*.wav)",
        )

        if file_path:
            self.settings.set_custom_sound(file_path)

    def save(self):
        self.settings.set_focus_minutes(self.focus_spin.value())
        self.settings.set_short_break_minutes(self.short_break_spin.value())
        self.settings.set_long_break_minutes(self.long_break_spin.value())
        self.settings.set_theme(self.theme_combo.currentText())
        self.settings.set_sound(self.sound_combo.currentText())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = AppSettings()
        self.timer = PomodoroTimer()
        self.sound_manager = SoundManager()

        self.mode = "Focus"
        self.session_number = 1

        self.setWindowTitle("Focus Flow")
        self.setMinimumSize(520, 620)
        self.resize(560, 680)

        self.build_ui()
        self.connect_signals()
        self.load_initial_timer()
        self.apply_theme()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(40, 35, 40, 35)
        self.main_layout.setSpacing(20)

        header_layout = QHBoxLayout()

        title = QLabel("FOCUS FLOW")
        title.setObjectName("title")

        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(44, 44)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_button)

        self.main_layout.addLayout(header_layout)

        self.status_label = QLabel("FOCUS SESSION")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setObjectName("status")

        self.main_layout.addWidget(self.status_label)

        self.timer_card = QFrame()
        self.timer_card.setObjectName("timerCard")

        timer_layout = QVBoxLayout(self.timer_card)
        timer_layout.setContentsMargins(25, 40, 25, 40)
        timer_layout.setSpacing(15)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setObjectName("timeLabel")

        self.session_label = QLabel("Session 1")
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_label.setObjectName("sessionLabel")

        timer_layout.addWidget(self.time_label)
        timer_layout.addWidget(self.session_label)

        self.main_layout.addWidget(self.timer_card)

        self.progress = QFrame()
        self.progress.setObjectName("progress")
        self.progress.setFixedHeight(8)

        self.main_layout.addWidget(self.progress)

        self.main_layout.addStretch()

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.reset_button = QPushButton("Reset")

        self.start_button.setObjectName("primaryButton")
        self.pause_button.setObjectName("secondaryButton")
        self.reset_button.setObjectName("secondaryButton")

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.pause_button)
        buttons_layout.addWidget(self.reset_button)

        self.main_layout.addLayout(buttons_layout)

        footer = QLabel("Focus deeply. Rest intentionally.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("footer")

        self.main_layout.addWidget(footer)

    def connect_signals(self):
        self.start_button.clicked.connect(self.start_timer)
        self.pause_button.clicked.connect(self.pause_timer)
        self.reset_button.clicked.connect(self.reset_timer)

        self.settings_button.clicked.connect(self.open_settings)

        self.timer.tick.connect(self.update_display)
        self.timer.finished.connect(self.timer_finished)

    def load_initial_timer(self):
        minutes = self.settings.get_focus_minutes()
        self.timer.reset(minutes * 60)
        self.update_display(self.timer.remaining_seconds)

    def start_timer(self):
        self.timer.start()

    def pause_timer(self):
        self.timer.pause()

    def reset_timer(self):
        if self.mode == "Focus":
            minutes = self.settings.get_focus_minutes()
        elif self.mode == "Short Break":
            minutes = self.settings.get_short_break_minutes()
        else:
            minutes = self.settings.get_long_break_minutes()

        self.timer.reset(minutes * 60)

    def update_display(self, seconds):
        minutes = seconds // 60
        remaining_seconds = seconds % 60

        self.time_label.setText(
            f"{minutes:02d}:{remaining_seconds:02d}"
        )

        if self.timer.total_seconds > 0:
            percentage = (
                (self.timer.total_seconds - seconds)
                / self.timer.total_seconds
            ) * 100

            self.progress.setFixedWidth(
                int(440 * (percentage / 100))
            )

    def timer_finished(self):
        self.sound_manager.play(
            self.settings.get_sound(),
            self.settings.get_custom_sound(),
        )

        if self.mode == "Focus":
            self.show_break_dialog()

        else:
            self.show_focus_dialog()

    def show_break_dialog(self):
        box = QMessageBox(self)

        box.setWindowTitle("Focus session complete")
        box.setText("Great work! Your focus session is complete.")
        box.setInformativeText("Would you like to start your break?")

        start_button = box.addButton(
            "Start Break",
            QMessageBox.ButtonRole.AcceptRole,
        )

        later_button = box.addButton(
            "Later",
            QMessageBox.ButtonRole.RejectRole,
        )

        box.exec()

        if box.clickedButton() == start_button:
            self.start_break()

    def show_focus_dialog(self):
        box = QMessageBox(self)

        box.setWindowTitle("Break complete")
        box.setText("Your break is finished.")
        box.setInformativeText("Ready for another focus session?")

        start_button = box.addButton(
            "Start Focus",
            QMessageBox.ButtonRole.AcceptRole,
        )

        box.addButton(
            "Later",
            QMessageBox.ButtonRole.RejectRole,
        )

        box.exec()

        if box.clickedButton() == start_button:
            self.start_focus()

    def start_break(self):
        self.mode = "Short Break"
        self.status_label.setText("SHORT BREAK")

        minutes = self.settings.get_short_break_minutes()

        self.timer.reset(minutes * 60)
        self.timer.start()

    def start_focus(self):
        self.mode = "Focus"
        self.session_number += 1

        self.status_label.setText("FOCUS SESSION")
        self.session_label.setText(
            f"Session {self.session_number}"
        )

        minutes = self.settings.get_focus_minutes()

        self.timer.reset(minutes * 60)
        self.timer.start()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save()

            self.apply_theme()

            if not self.timer.is_running():
                self.reset_timer()

    def apply_theme(self):
        theme = get_theme(self.settings.get_theme())

        background = (
            self.settings.get_background_color()
            or theme["background"]
        )

        accent = (
            self.settings.get_accent_color()
            or theme["accent"]
        )

        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: {background};
            }}

            QWidget {{
                color: {theme["text"]};
                font-family: "SF Pro Display", "Helvetica Neue", sans-serif;
            }}

            QLabel#title {{
                font-size: 22px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            QLabel#status {{
                color: {theme["secondary_text"]};
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 2px;
            }}

            QFrame#timerCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 28px;
            }}

            QLabel#timeLabel {{
                font-size: 76px;
                font-weight: 300;
            }}

            QLabel#sessionLabel {{
                color: {theme["secondary_text"]};
                font-size: 15px;
            }}

            QPushButton {{
                border-radius: 12px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 600;
            }}

            QPushButton#primaryButton {{
                background: {accent};
                color: {theme["button_text"]};
                border: none;
            }}

            QPushButton#primaryButton:hover {{
                opacity: 0.9;
            }}

            QPushButton#secondaryButton {{
                background: {theme["card"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
            }}

            QPushButton#settingsButton {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
                font-size: 18px;
            }}

            QLabel#footer {{
                color: {theme["secondary_text"]};
                font-size: 12px;
            }}

            QSpinBox, QComboBox {{
                padding: 8px;
                border: 1px solid {theme["border"]};
                border-radius: 8px;
            }}
            """
        )

        self.progress.setStyleSheet(
            f"""
            QFrame#progress {{
                background: {accent};
                border-radius: 4px;
            }}
            """
        )