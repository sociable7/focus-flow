from PySide6.QtCore import (
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FloatingTimer(QWidget):
    """
    Small always-on-top timer window.

    It shares the same PomodoroTimer instance
    as the main window.
    """

    close_requested = Signal()

    def __init__(
        self,
        timer,
        parent=None,
        toggle_callback=None,
    ):
        super().__init__(parent)

        self.timer = timer
        self.toggle_callback = toggle_callback
        self.drag_position = QPoint()

        self.setWindowTitle(
            "Focus Flow"
        )

        self.setFixedSize(
            236,
            170,
        )

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # On macOS, Qt::Tool maps to NSPanel and is hidden when the owning
        # application deactivates unless this attribute is enabled.
        self.setAttribute(
            Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow,
            True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )

        self.build_ui()
        self.connect_signals()
        self.apply_theme()

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):
        self.container = QFrame()

        self.container.setObjectName(
            "floatingContainer"
        )

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.addWidget(
            self.container
        )

        container_layout = QVBoxLayout(
            self.container
        )

        container_layout.setContentsMargins(
            16,
            12,
            16,
            14,
        )

        container_layout.setSpacing(6)

        # -----------------------------------------------------
        # Top row
        # -----------------------------------------------------

        top_layout = QHBoxLayout()

        self.mode_label = QLabel(
            "FOCUS"
        )

        self.mode_label.setObjectName(
            "modeLabel"
        )

        self.close_button = QPushButton(
            "×"
        )

        self.close_button.setObjectName(
            "closeButton"
        )

        self.close_button.setFixedSize(
            24,
            24,
        )

        self.close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        top_layout.addWidget(
            self.mode_label
        )

        top_layout.addStretch()

        top_layout.addWidget(
            self.close_button
        )

        container_layout.addLayout(
            top_layout
        )

        self.task_label = QLabel()
        self.task_label.setObjectName("taskLabel")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setWordWrap(False)
        self.task_label.hide()
        container_layout.addWidget(self.task_label)

        # -----------------------------------------------------
        # Timer
        # -----------------------------------------------------

        self.time_label = QLabel(
            "25:00"
        )

        self.time_label.setObjectName(
            "timeLabel"
        )

        self.time_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        font = QFont()

        font.setPointSize(32)
        font.setWeight(
            QFont.Weight.DemiBold
        )

        self.time_label.setFont(font)

        container_layout.addWidget(
            self.time_label
        )

        # -----------------------------------------------------
        # Pause button
        # -----------------------------------------------------

        self.pause_button = QPushButton(
            "Pause"
        )

        self.pause_button.setObjectName(
            "pauseButton"
        )

        self.pause_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        container_layout.addWidget(
            self.pause_button
        )

    # =========================================================
    # Signals
    # =========================================================

    def connect_signals(self):
        self.timer.tick.connect(
            self.update_time
        )

        self.timer.finished.connect(
            self.timer_finished
        )

        self.pause_button.clicked.connect(
            self.toggle_timer
        )

        self.close_button.clicked.connect(
            self.close_requested.emit
        )

    # =========================================================
    # Timer
    # =========================================================

    def update_time(self, seconds):
        minutes = seconds // 60
        remaining_seconds = seconds % 60

        self.time_label.setText(
            f"{minutes:02d}:{remaining_seconds:02d}"
        )

        self.update_pause_button()

    def toggle_timer(self):
        if self.toggle_callback is not None:
            self.toggle_callback()
            self.update_pause_button()
            return

        if self.timer.is_running():
            self.timer.pause()

        else:
            self.timer.start()

        self.update_pause_button()

    def update_pause_button(self):
        if self.timer.is_running():
            self.pause_button.setText(
                "Pause"
            )

        else:
            self.pause_button.setText(
                "Start"
            )

    def timer_finished(self):
        self.pause_button.setText(
            "Start"
        )

    def set_mode(self, mode):
        self.mode_label.setText(
            mode.upper()
        )

    def set_task_name(self, task_name):
        task_name = task_name.strip()
        self.task_label.setText(task_name)
        self.task_label.setVisible(bool(task_name))

    # =========================================================
    # Dragging
    # =========================================================

    def mousePressEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons()
            & Qt.MouseButton.LeftButton
        ):
            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )

            event.accept()

    # =========================================================
    # Styling
    # =========================================================

    def apply_theme(self, theme=None, accent=None):
        theme = theme or {
            "surface": "#191B20",
            "surface_alt": "#22252C",
            "text": "#F5F5F7",
            "secondary_text": "#A1A1AA",
            "accent": "#8B5CF6",
            "button_text": "#FFFFFF",
            "border": "#30333B",
        }
        accent = accent or theme["accent"]

        self.setStyleSheet(
            f"""
            QWidget {{
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    sans-serif;
            }}

            QFrame#floatingContainer {{
                background: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}

            QLabel#modeLabel {{
                color: {theme["secondary_text"]};
                font-size: 10px;
                font-weight: 700;
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
            """
        )
