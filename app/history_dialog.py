from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.themes import get_theme


class HistoryDialog(QDialog):
    """A compact view of completed focus sessions stored by HistoryManager."""

    def __init__(self, history, settings, parent=None):
        super().__init__(parent)
        self.history = history
        self.settings = settings

        self.setWindowTitle("Focus Flow History")
        self.setMinimumSize(620, 480)
        self.resize(680, 560)

        self.build_ui()
        self.refresh()
        self.apply_theme()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)

        title = QLabel("History")
        title.setObjectName("historyTitle")
        subtitle = QLabel("Completed focus sessions")
        subtitle.setObjectName("historySubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        summary = QHBoxLayout()
        summary.setSpacing(12)
        self.today_value = self._summary_value("Today")
        self.week_value = self._summary_value("This Week")
        self.total_value = self._summary_value("Total Focus Time")
        for value in (self.today_value, self.week_value, self.total_value):
            summary.addWidget(value)
        layout.addLayout(summary)

        self.sessions_table = QTableWidget(0, 3)
        self.sessions_table.setObjectName("historyTable")
        self.sessions_table.setHorizontalHeaderLabels(
            ["Date & Time", "Task", "Duration"]
        )
        self.sessions_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.sessions_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.verticalHeader().setVisible(False)
        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.sessions_table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _summary_value(title):
        label = QLabel()
        label.setObjectName("historySummary")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setProperty("summaryTitle", title)
        return label

    def refresh(self):
        sessions = self.history.get_all()
        today = self.history.get_today_total()
        week = self.history.get_this_week_total()
        total = sum(duration for _, _, duration in sessions)

        self._set_summary(self.today_value, "Today", today)
        self._set_summary(self.week_value, "This Week", week)
        self._set_summary(self.total_value, "Total Focus Time", total)

        self.sessions_table.setRowCount(0)
        for task, start_time, duration in sessions[:50]:
            row = self.sessions_table.rowCount()
            self.sessions_table.insertRow(row)
            self.sessions_table.setItem(
                row, 0, QTableWidgetItem(self._format_datetime(start_time))
            )
            self.sessions_table.setItem(row, 1, QTableWidgetItem(task))
            self.sessions_table.setItem(
                row, 2, QTableWidgetItem(self._format_duration(duration))
            )

        if not sessions:
            self.sessions_table.setRowCount(1)
            empty = QTableWidgetItem("No completed focus sessions yet.")
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_table.setItem(0, 0, empty)
            self.sessions_table.setSpan(0, 0, 1, 3)

    def _set_summary(self, label, title, seconds):
        label.setText(f"{title}\n{self._format_duration(seconds)}")

    @staticmethod
    def _format_duration(seconds):
        hours, remainder = divmod(int(seconds), 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"

    @staticmethod
    def _format_datetime(value):
        try:
            return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
        except (TypeError, ValueError):
            return str(value)

    def apply_theme(self):
        theme = get_theme(self.settings.get_theme())
        background = self.settings.get_background_color() or theme["background"]
        accent = self.settings.get_accent_color() or theme["accent"]
        self.setStyleSheet(
            f"""
            QDialog {{ background: {background}; color: {theme["text"]}; }}
            QLabel#historyTitle {{ font-size: 25px; font-weight: 700; }}
            QLabel#historySubtitle {{ color: {theme["secondary_text"]}; }}
            QLabel#historySummary {{
                background: {theme["surface"]}; border: 1px solid {theme["border"]};
                border-radius: 12px; padding: 14px; font-weight: 600;
            }}
            QTableWidget#historyTable {{
                background: {theme["surface"]}; border: 1px solid {theme["border"]};
                border-radius: 12px; gridline-color: {theme["border"]};
            }}
            QHeaderView::section {{
                background: {theme["surface_alt"]}; color: {theme["secondary_text"]};
                border: none; border-bottom: 1px solid {theme["border"]}; padding: 9px;
                font-weight: 700;
            }}
            QTableWidget::item {{ padding: 7px; }}
            QTableWidget::item:selected {{ background: {accent}; color: {theme["button_text"]}; }}
            QPushButton {{
                background: {theme["surface_alt"]}; color: {theme["text"]};
                border: 1px solid {theme["border"]}; border-radius: 8px; padding: 7px 14px;
            }}
            """
        )
