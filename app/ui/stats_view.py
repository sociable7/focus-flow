"""Stats view: totals, 14-day chart and per-task breakdown."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import (
    BarChart,
    CardRow,
    StreakStrip,
    format_duration,
    format_weekday,
    make_page_header,
)


class StatsView(QWidget):
    """Read-only analytics backed by ``SessionRepository``."""

    def __init__(self, session_repo, parent=None):
        super().__init__(parent)
        self.repo = session_repo
        self.build_ui()
        self.refresh()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 28)
        layout.setSpacing(14)

        layout.addWidget(
            make_page_header(
                "Stats", "How your focus time adds up"
            )
        )

        self.cards = CardRow(
            ["Total", "Sessions", "7-Day Avg", "Day Streak"]
        )
        layout.addWidget(self.cards)

        chart_title = QLabel("Last 14 days")
        chart_title.setObjectName("sectionTitle")
        layout.addWidget(chart_title)

        self.chart = BarChart()
        self.chart.setAccessibleName("Focus time chart")
        layout.addWidget(self.chart)

        streak_title = QLabel("Day streak")
        streak_title.setObjectName("sectionTitle")
        layout.addWidget(streak_title)

        self.streak_strip = StreakStrip()
        layout.addWidget(self.streak_strip)

        tasks_title = QLabel("Top tasks")
        tasks_title.setObjectName("sectionTitle")
        layout.addWidget(tasks_title)

        self.task_rows = QVBoxLayout()
        self.task_rows.setSpacing(8)
        layout.addLayout(self.task_rows)

        layout.addStretch()

    # =====================================================
    # Data
    # =====================================================

    def refresh(self):
        total = self.repo.lifetime_total()
        count = self.repo.session_count()
        streak = self.repo.day_streak()
        week = self.repo.daily_series(7)
        avg = sum(seconds for _, seconds in week) // 7

        self.cards.values["Total"].setText(format_duration(total))
        self.cards.values["Sessions"].setText(str(count))
        self.cards.values["7-Day Avg"].setText(format_duration(avg))
        self.cards.values["Day Streak"].setText(
            f"{streak} day{'s' if streak != 1 else ''}"
        )

        fortnight = self.repo.daily_series(14)
        self.chart.set_data(
            [
                (format_weekday(day), seconds)
                for day, seconds in fortnight
            ]
        )
        self.chart.setAccessibleDescription(
            "Daily focus minutes for the last 14 days."
        )

        self.streak_strip.set_data(week, streak)

        while self.task_rows.count():
            item = self.task_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        breakdown = self.repo.per_task(5)
        peak = breakdown[0][1] if breakdown else 0
        if not breakdown:
            empty = QLabel("No completed sessions yet.")
            empty.setObjectName("pageSubtitle")
            self.task_rows.addWidget(empty)
            return

        for task, seconds, _sessions in breakdown:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            name = QLabel(task)
            name.setObjectName("taskRowName")
            name.setMinimumWidth(140)
            name.setMaximumWidth(220)
            name.setWordWrap(False)
            name.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )
            row_layout.addWidget(name)

            bar = QProgressBar()
            bar.setObjectName("taskRowBar")
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setValue(
                int(seconds / peak * 100) if peak else 0
            )
            row_layout.addWidget(bar, 1)

            value = QLabel(format_duration(seconds))
            value.setObjectName("taskRowValue")
            value.setMinimumWidth(52)
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(value)

            self.task_rows.addWidget(row)
