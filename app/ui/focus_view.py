"""Focus view: task, timer card, progress, goal and controls.

Presentation-only. All timer decisions live in ``SessionEngine``; this
view exposes its widgets so ``MainWindow`` keeps its public attribute
surface, and emits action signals the window connects to its slots.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FocusView(QWidget):
    start_requested = Signal()
    pause_requested = Signal()
    reset_requested = Signal()
    skip_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._completion_callback = None
        self._completion_active = False
        self.build_ui()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 28)
        layout.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(2)

        title = QLabel("Focus Flow")
        title.setObjectName("appTitle")
        header.addWidget(title)

        subtitle = QLabel("Focus deeply. Rest intentionally.")
        subtitle.setObjectName("appSubtitle")
        header.addWidget(subtitle)

        layout.addLayout(header)

        task_label = QLabel("What are you focusing on?")
        task_label.setObjectName("taskLabel")
        layout.addWidget(task_label)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("e.g. Build Focus Flow")
        self.task_input.setObjectName("taskInput")
        self.task_input.setClearButtonEnabled(True)
        self.task_input.setAccessibleName("Focus task")
        self.task_input.setAccessibleDescription(
            "Describe what you want to focus on, then press Start."
        )
        layout.addWidget(self.task_input)

        self.mode_label = QLabel("FOCUS SESSION")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_label.setObjectName("modeLabel")
        layout.addWidget(self.mode_label)

        self.timer_card = QFrame()
        self.timer_card.setObjectName("timerCard")

        card_layout = QVBoxLayout(self.timer_card)
        card_layout.setContentsMargins(30, 40, 30, 36)
        card_layout.setSpacing(10)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setObjectName("timeLabel")
        self.time_label.setAccessibleName("Time remaining")
        card_layout.addWidget(self.time_label)

        self.session_label = QLabel("Session 1 of 4")
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_label.setObjectName("sessionLabel")
        card_layout.addWidget(self.session_label)

        layout.addWidget(self.timer_card)

        self.progress = QProgressBar()
        self.progress.setObjectName("progressBar")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        layout.addWidget(self.progress)

        dots_layout = QHBoxLayout()
        dots_layout.setSpacing(8)
        dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.session_dots = []
        for _ in range(12):
            dot = QFrame()
            dot.setFixedSize(9, 9)
            dot.setObjectName("sessionDot")
            dots_layout.addWidget(dot)
            self.session_dots.append(dot)
        layout.addLayout(dots_layout)

        self.goal_label = QLabel()
        self.goal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.goal_label.setObjectName("goalLabel")
        layout.addWidget(self.goal_label)

        self.goal_progress = QProgressBar()
        self.goal_progress.setObjectName("goalProgressBar")
        self.goal_progress.setTextVisible(False)
        self.goal_progress.setFixedHeight(5)
        layout.addWidget(self.goal_progress)

        self.build_completion_banner(layout)

        layout.addStretch()

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.reset_button = QPushButton("Reset")
        self.pause_button = QPushButton("Pause")
        self.start_button = QPushButton("Start")
        self.skip_button = QPushButton("Skip")

        self.reset_button.setAccessibleName("Reset timer")
        self.pause_button.setAccessibleName("Pause timer")
        self.start_button.setAccessibleName("Start timer")
        self.skip_button.setAccessibleName("Skip break")
        self.skip_button.setAccessibleDescription(
            "Ends the current break and prepares the next focus session."
        )

        self.reset_button.setObjectName("secondaryButton")
        self.pause_button.setObjectName("secondaryButton")
        self.start_button.setObjectName("primaryButton")
        self.skip_button.setObjectName("secondaryButton")
        self.skip_button.setToolTip("Skip the current break")

        for button in (
            self.reset_button,
            self.pause_button,
            self.start_button,
            self.skip_button,
        ):
            button.setMinimumHeight(46)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        controls.addWidget(self.reset_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.start_button)
        controls.addWidget(self.skip_button)
        layout.addLayout(controls)

        self.footer_label = QLabel()
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setObjectName("footerLabel")
        layout.addWidget(self.footer_label)

        self.reset_button.clicked.connect(self.reset_requested.emit)
        self.pause_button.clicked.connect(self.pause_requested.emit)
        self.start_button.clicked.connect(self.start_requested.emit)
        self.skip_button.clicked.connect(self.skip_requested.emit)

    def build_completion_banner(self, layout):
        self.banner = QFrame()
        self.banner.setObjectName("completionBanner")

        banner_layout = QVBoxLayout(self.banner)
        banner_layout.setContentsMargins(16, 14, 16, 14)
        banner_layout.setSpacing(8)

        self.banner_title = QLabel()
        self.banner_title.setObjectName("bannerTitle")
        self.banner_title.setWordWrap(True)
        banner_layout.addWidget(self.banner_title)

        self.banner_message = QLabel()
        self.banner_message.setObjectName("bannerMessage")
        self.banner_message.setWordWrap(True)
        banner_layout.addWidget(self.banner_message)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.banner_action = QPushButton()
        self.banner_action.setObjectName("primaryButton")
        self.banner_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.banner_action.clicked.connect(self._on_banner_action)
        buttons.addWidget(self.banner_action, 1)

        later = QPushButton("Later")
        later.setObjectName("secondaryButton")
        later.setCursor(Qt.CursorShape.PointingHandCursor)
        later.clicked.connect(self.hide_completion)
        buttons.addWidget(later)

        banner_layout.addLayout(buttons)
        layout.addWidget(self.banner)
        self.banner.hide()

    # =====================================================
    # Completion banner (non-modal phase transitions)
    # =====================================================

    def show_completion(self, title, message, action_text, callback):
        self.banner_title.setText(title)
        self.banner_message.setText(message)
        self.banner_action.setText(action_text)
        self._completion_callback = callback
        self._completion_active = True
        self.banner.show()

    def hide_completion(self):
        self.banner.hide()
        self._completion_callback = None
        self._completion_active = False

    def is_completion_visible(self):
        return self.banner.isVisible()

    def is_completion_active(self):
        """Banner state independent of ancestor visibility (testable)."""
        return self._completion_active

    def _on_banner_action(self):
        callback, self._completion_callback = (
            self._completion_callback,
            None,
        )
        self._completion_active = False
        self.banner.hide()
        if callback is not None:
            callback()

    # =====================================================
    # Goal progress
    # =====================================================

    def set_goal_progress(self, done_minutes, goal_minutes):
        if goal_minutes > 0:
            self.goal_progress.setValue(
                min(100, int(done_minutes / goal_minutes * 100))
            )
        else:
            self.goal_progress.setValue(0)
