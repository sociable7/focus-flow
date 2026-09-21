"""Shared UI primitives: formatters, stat cards and a bar chart.

All widgets here are presentation-only. Data comes from the repository
and service layers; see the individual views.
"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def format_duration(seconds):
    """Compact duration: ``25m`` or ``1h 05m``."""
    hours, remainder = divmod(int(seconds or 0), 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def format_datetime(value):
    """Human-readable session timestamp; never raises."""
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return str(value)


def format_weekday(day_iso):
    try:
        return datetime.fromisoformat(day_iso).strftime("%a")
    except (TypeError, ValueError):
        return str(day_iso)


def elided(text, font, width):
    """Elide long strings so task names never break layouts."""
    metrics = QFontMetrics(font)
    return metrics.elidedText(
        str(text), Qt.TextElideMode.ElideRight, max(0, width)
    )


def make_stat_card(title):
    """A small summary card; returns ``(frame, value_label)``."""
    frame = QFrame()
    frame.setObjectName("statCard")

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(4)

    title_label = QLabel(title)
    title_label.setObjectName("statTitle")
    layout.addWidget(title_label)

    value_label = QLabel("—")
    value_label.setObjectName("statValue")
    value_label.setWordWrap(True)
    layout.addWidget(value_label)

    return frame, value_label


def make_page_header(title, subtitle):
    """Consistent view header; returns the layout-ready widget."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    title_label = QLabel(title)
    title_label.setObjectName("pageTitle")
    layout.addWidget(title_label)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("pageSubtitle")
    layout.addWidget(subtitle_label)

    return container


class BarChart(QWidget):
    """Minimal custom-painted vertical bar chart (no QtCharts).

    Data is ``[(label, value), ...]``. Zero/max handling and the empty
    state are built in; colors come from the current palette via dynamic
    properties set by the owning view (``bar_accent`` / ``bar_track``).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._accent = "#8B5CF6"
        self._track = "#30333B"
        self._text = "#A1A1AA"
        self.setMinimumHeight(150)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def set_data(self, data):
        self._data = [(str(label), max(0, value)) for label, value in data]
        self.update()

    def set_colors(self, accent, track, text):
        self._accent = accent
        self._track = track
        self._text = text
        self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize

        return QSize(400, 170)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(6, 6, -6, 26)
        if not self._data:
            painter.setPen(self._text)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No data yet — complete a focus session.",
            )
            return

        maximum = max(value for _, value in self._data) or 1
        slot = rect.width() / max(1, len(self._data))
        bar_width = max(4.0, min(34.0, slot * 0.55))

        for index, (label, value) in enumerate(self._data):
            center = rect.left() + slot * index + slot / 2
            height = (rect.height() - 8) * (value / maximum)
            top = rect.bottom() - height
            painter.fillRect(
                int(center - bar_width / 2),
                int(top),
                int(bar_width),
                int(height),
                self._accent if value else self._track,
            )
            painter.setPen(self._text)
            painter.drawText(
                int(center - slot / 2),
                self.height() - 20,
                int(slot),
                20,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )


class CardRow(QWidget):
    """Horizontal row of equally-stretched stat cards."""

    def __init__(self, titles, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.values = {}
        for title in titles:
            card, value = make_stat_card(title)
            layout.addWidget(card, 1)
            self.values[title] = value


class StreakStrip(QWidget):
    """Custom-painted 7-day activity strip (Group 4).

    Data is ``[(day_iso, seconds), ...]`` (oldest first) plus the
    current day-streak count. Days with focus time render as filled
    accent dots, empty days as track rings; today gets a bold outline.
    Pure presentation: all values come from ``SessionRepository``.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._days = []
        self._streak = 0
        self._accent = "#8B5CF6"
        self._track = "#30333B"
        self._text = "#A1A1AA"
        self.setMinimumHeight(64)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setAccessibleName("7-day activity")
        self._update_accessible_description()

    def set_data(self, days, streak=0):
        self._days = [(str(day), max(0, seconds)) for day, seconds in days]
        self._streak = max(0, int(streak or 0))
        self._update_accessible_description()
        self.update()

    def set_colors(self, accent, track, text):
        self._accent = accent
        self._track = track
        self._text = text
        self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize

        return QSize(400, 64)

    def _update_accessible_description(self):
        active = sum(1 for _, seconds in self._days if seconds > 0)
        self.setAccessibleDescription(
            f"{active} of {len(self._days)} days active."
            f" Current streak: {self._streak} days."
        )

    def paintEvent(self, event):
        from PySide6.QtGui import QColor, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._days:
            painter.setPen(self._text)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No activity yet — complete a focus session.",
            )
            return

        count = len(self._days)
        slot = self.width() / max(1, count)
        center_y = 22.0
        radius = max(6.0, min(11.0, slot * 0.22))

        for index, (day, seconds) in enumerate(self._days):
            center_x = slot * index + slot / 2
            is_today = index == count - 1
            if seconds > 0:
                painter.setBrush(QColor(self._accent))
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(self._track), 2))
            painter.drawEllipse(
                int(center_x - radius),
                int(center_y - radius),
                int(radius * 2),
                int(radius * 2),
            )
            if is_today:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(self._accent), 2))
                painter.drawEllipse(
                    int(center_x - radius - 3),
                    int(center_y - radius - 3),
                    int((radius + 3) * 2),
                    int((radius + 3) * 2),
                )
            painter.setPen(self._text)
            painter.drawText(
                int(center_x - slot / 2),
                40,
                int(slot),
                20,
                Qt.AlignmentFlag.AlignCenter,
                format_weekday(day),
            )
