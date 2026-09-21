"""Goals view: today's target, progress, streak and recent history."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import (
    CardRow,
    format_duration,
    make_page_header,
)


class GoalsView(QWidget):
    """Daily goal management backed by ``GoalService`` + repository."""

    def __init__(self, goal_service, session_repo, parent=None):
        super().__init__(parent)
        self.goal_service = goal_service
        self.repo = session_repo
        self.build_ui()
        self.refresh()
        self.goal_service.valueChanged.connect(
            lambda _key: self.refresh()
        )

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 28)
        layout.setSpacing(14)

        layout.addWidget(
            make_page_header(
                "Goals", "A daily target, tracked automatically"
            )
        )

        self.cards = CardRow(["Today", "Goal", "Day Streak"])
        layout.addWidget(self.cards)

        editor = QFrame()
        editor.setObjectName("editorCard")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(18, 16, 18, 16)
        editor_layout.setSpacing(10)

        editor_title = QLabel("Daily focus goal")
        editor_title.setObjectName("sectionTitle")
        editor_layout.addWidget(editor_title)

        form = QHBoxLayout()
        form.setSpacing(10)

        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(15, 1440)
        self.goal_spin.setSuffix(" min")
        self.goal_spin.setAccessibleName("Daily focus goal")
        self.goal_spin.setMinimumWidth(140)
        form.addWidget(self.goal_spin)

        form.addStretch()

        self.save_button = QPushButton("Save Goal")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self._on_save)
        form.addWidget(self.save_button)

        editor_layout.addLayout(form)

        self.progress = QProgressBar()
        self.progress.setObjectName("progressBar")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        editor_layout.addWidget(self.progress)

        self.status_label = QLabel()
        self.status_label.setObjectName("pageSubtitle")
        self.status_label.setWordWrap(True)
        editor_layout.addWidget(self.status_label)

        layout.addWidget(editor)

        recent_title = QLabel("Recent targets")
        recent_title.setObjectName("sectionTitle")
        layout.addWidget(recent_title)

        self.goals_table = QTableWidget(0, 2)
        self.goals_table.setObjectName("dataTable")
        self.goals_table.setAccessibleName("Recent daily targets")
        self.goals_table.setHorizontalHeaderLabels(
            ["Date", "Target"]
        )
        self.goals_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.goals_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.goals_table.setAlternatingRowColors(True)
        self.goals_table.verticalHeader().setVisible(False)
        header = self.goals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.goals_table, 1)

    # =====================================================
    # Data
    # =====================================================

    def refresh(self):
        goal = self.goal_service.get_daily_goal_minutes()
        done_seconds = self.repo.today_total()
        done_minutes = done_seconds // 60
        streak = self.repo.day_streak()

        if self.goal_spin.value() != goal:
            self.goal_spin.setValue(goal)

        self.cards.values["Today"].setText(
            format_duration(done_seconds)
        )
        self.cards.values["Goal"].setText(format_duration(goal * 60))
        self.cards.values["Day Streak"].setText(
            f"{streak} day{'s' if streak != 1 else ''}"
        )

        if goal > 0:
            self.progress.setValue(
                min(100, int(done_minutes / goal * 100))
            )
        else:
            self.progress.setValue(0)

        if done_minutes >= goal:
            self.status_label.setText(
                f"Daily goal complete — {done_minutes} / {goal} min."
            )
        else:
            self.status_label.setText(
                f"{done_minutes} / {goal} min so far —"
                f" {goal - done_minutes} min to go."
            )

        recent = self.goal_service.goals.get_recent_goals(14)
        self.goals_table.setRowCount(0)
        for day, target in recent:
            row = self.goals_table.rowCount()
            self.goals_table.insertRow(row)
            self.goals_table.setItem(row, 0, QTableWidgetItem(day))
            self.goals_table.setItem(
                row, 1, QTableWidgetItem(format_duration(target * 60))
            )
        if not recent:
            self.goals_table.setRowCount(1)
            empty = QTableWidgetItem(
                "No saved targets yet — set one above."
            )
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.goals_table.setItem(0, 0, empty)
            self.goals_table.setSpan(0, 0, 1, 2)

    def _on_save(self):
        self.goal_service.set_daily_goal_minutes(self.goal_spin.value())
        self.refresh()
