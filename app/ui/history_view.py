"""History view: summaries, search/filter, paginated sessions, export."""

import csv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import (
    CardRow,
    format_datetime,
    format_duration,
    make_page_header,
)

PAGE_SIZE = 50

RANGES = ("All time", "Today", "This week")


class HistoryView(QWidget):
    """Embedded history page backed by ``SessionRepository``."""

    def __init__(self, session_repo, parent=None):
        super().__init__(parent)
        self.repo = session_repo
        self._offset = 0
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
            make_page_header("History", "Completed focus sessions")
        )

        self.cards = CardRow(
            ["Today", "This Week", "Total", "Day Streak"]
        )
        layout.addWidget(self.cards)

        self.notice_label = QLabel()
        self.notice_label.setObjectName("noticeLabel")
        self.notice_label.setWordWrap(True)
        self.notice_label.hide()
        layout.addWidget(self.notice_label)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks…")
        self.search_input.setObjectName("searchInput")
        self.search_input.setAccessibleName("Search sessions")
        self.search_input.setClearButtonEnabled(True)
        filters.addWidget(self.search_input, 1)

        self.task_combo = QComboBox()
        self.task_combo.setObjectName("filterCombo")
        self.task_combo.setMinimumWidth(150)
        filters.addWidget(self.task_combo)

        self.range_combo = QComboBox()
        self.range_combo.setObjectName("filterCombo")
        self.range_combo.addItems(RANGES)
        filters.addWidget(self.range_combo)

        layout.addLayout(filters)

        self.sessions_table = QTableWidget(0, 3)
        self.sessions_table.setObjectName("dataTable")
        self.sessions_table.setAccessibleName("Completed sessions")
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

        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.prev_button = QPushButton("← Newer")
        self.prev_button.setObjectName("secondaryButton")
        self.prev_button.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom.addWidget(self.prev_button)

        self.page_label = QLabel("Page 1")
        self.page_label.setObjectName("pageLabel")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.addWidget(self.page_label, 1)

        self.next_button = QPushButton("Older →")
        self.next_button.setObjectName("secondaryButton")
        self.next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom.addWidget(self.next_button)

        self.export_button = QPushButton("Export CSV")
        self.export_button.setObjectName("secondaryButton")
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom.addWidget(self.export_button)

        layout.addLayout(bottom)

        self.search_input.textChanged.connect(self._on_filter_changed)
        self.search_input.returnPressed.connect(self.refresh)
        self.task_combo.currentIndexChanged.connect(self.refresh)
        self.range_combo.currentIndexChanged.connect(self.refresh)
        self.prev_button.clicked.connect(self._on_prev)
        self.next_button.clicked.connect(self._on_next)
        self.export_button.clicked.connect(self._on_export)

    # =====================================================
    # Data
    # =====================================================

    def _current_task_filter(self):
        text = self.task_combo.currentText()
        if not text or text == "All tasks":
            return ""
        return text

    def _date_bounds(self):
        from datetime import datetime, timedelta

        choice = self.range_combo.currentText()
        if choice == "Today":
            today = datetime.now().date().isoformat()
            return today, today
        if choice == "This week":
            today = datetime.now().date()
            start = today - timedelta(days=today.weekday())
            return start.isoformat(), today.isoformat()
        return "", ""

    def _fetch_page(self):
        date_from, date_to = self._date_bounds()
        rows = self.repo.page(
            limit=PAGE_SIZE + 1,
            offset=self._offset,
            task_query=self.search_input.text().strip()
            or self._current_task_filter(),
            date_from=date_from,
            date_to=date_to,
        )
        return rows

    def refresh(self):
        if not self.repo.database.is_available:
            self.notice_label.setText(
                "Session history is unavailable."
                " Check the application data folder."
            )
            self.notice_label.setToolTip(
                self.repo.database.error_message
            )
            self.notice_label.show()
        else:
            self.notice_label.hide()
            self.notice_label.setToolTip("")

        self.cards.values["Today"].setText(
            format_duration(self.repo.today_total())
        )
        self.cards.values["This Week"].setText(
            format_duration(self.repo.week_total())
        )
        self.cards.values["Total"].setText(
            format_duration(self.repo.lifetime_total())
        )
        streak = self.repo.day_streak()
        self.cards.values["Day Streak"].setText(
            f"{streak} day{'s' if streak != 1 else ''}"
        )

        current_tasks = {
            self.task_combo.itemText(index)
            for index in range(self.task_combo.count())
        }
        # Block signals while repopulating: adding the first item would
        # otherwise re-enter refresh() via currentIndexChanged and append
        # the same tasks a second time.
        self.task_combo.blockSignals(True)
        try:
            if "All tasks" not in current_tasks:
                if self.task_combo.count() == 0:
                    self.task_combo.addItem("All tasks")
                else:
                    self.task_combo.insertItem(0, "All tasks")
                current_tasks.add("All tasks")
            for task in self.repo.tasks():
                if task not in current_tasks:
                    self.task_combo.addItem(task)
                    current_tasks.add(task)
            if self.task_combo.currentIndex() < 0:
                self.task_combo.setCurrentIndex(0)
        finally:
            self.task_combo.blockSignals(False)

        rows = self._fetch_page()
        self._has_next = len(rows) > PAGE_SIZE
        self._render_table(rows[:PAGE_SIZE])
        self._render_pager()

    def _render_table(self, rows):
        self.sessions_table.setRowCount(0)
        for task, start_time, duration in rows:
            row = self.sessions_table.rowCount()
            self.sessions_table.insertRow(row)
            self.sessions_table.setItem(
                row, 0, QTableWidgetItem(format_datetime(start_time))
            )
            self.sessions_table.setItem(row, 1, QTableWidgetItem(task))
            self.sessions_table.setItem(
                row, 2, QTableWidgetItem(format_duration(duration))
            )

        if not rows:
            self.sessions_table.setRowCount(1)
            empty = QTableWidgetItem("No sessions match these filters.")
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_table.setItem(0, 0, empty)
            self.sessions_table.setSpan(0, 0, 1, 3)

    def _render_pager(self):
        page = self._offset // PAGE_SIZE + 1
        self.page_label.setText(f"Page {page}")
        self.prev_button.setEnabled(self._offset > 0)
        self.next_button.setEnabled(self._has_next)

    # =====================================================
    # Interactions
    # =====================================================

    def _on_filter_changed(self):
        self._offset = 0
        # Debounce-free live search is fine at this data volume, but the
        # offset must reset before re-rendering the first page.
        self.refresh()

    def _on_prev(self):
        self._offset = max(0, self._offset - PAGE_SIZE)
        self.refresh()

    def _on_next(self):
        if self._has_next:
            self._offset += PAGE_SIZE
            self.refresh()

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History",
            "focus-flow-history.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.export_to_csv(path)

    def export_to_csv(self, path):
        """Write all filtered rows to ``path``; returns the row count."""
        date_from, date_to = self._date_bounds()
        rows = self.repo.page(
            limit=1000000,
            offset=0,
            task_query=self.search_input.text().strip()
            or self._current_task_filter(),
            date_from=date_from,
            date_to=date_to,
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["start_time", "task", "duration_seconds"])
            writer.writerows(
                [(start, task, duration) for task, start, duration in rows]
            )
        return len(rows)
