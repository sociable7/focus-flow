"""Shared circular progress ring for the main and floating timers.

Both windows show the same thin, theme-derived ring around the timer
number: the widget paints a quiet full-circle track plus a slightly
stronger elapsed arc (tones from ``theme_service.ring_palette``),
sweeping clockwise from 12 o'clock.

Progress is display-only. ``RingProgressBinding`` derives it from the
shared ``Clock`` (see ``app.core.clock`` / ``SessionEngine`` — the
single source of truth) and glides between the clock's whole-second
ticks; it never starts, owns or duplicates a countdown. One binding
instance drives one ring, so both windows mirror the exact same
timer/session state through pause, resume, skip and completion.
"""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ProgressRing(QWidget):
    """Circular progress arc showing elapsed session time.

    Sized by the owning view: the floating timer keeps the compact
    default, the main timer card uses a larger ring (same pen weight,
    same tones) so both read as one visual language. Display-only —
    progress is pushed in via ``set_progress``; this widget owns no
    timer state of its own.
    """

    RING_SIZE = 160
    PEN_WIDTH = 5

    def __init__(self, parent=None, size=None, pen_width=None):
        super().__init__(parent)
        self._progress = 0.0
        self._track_color = QColor("#E8E8EC")
        self._arc_color = QColor("#D2D2D7")
        self._ring_size = int(size) if size else self.RING_SIZE
        self._pen_width = int(pen_width) if pen_width else self.PEN_WIDTH
        self.setFixedSize(self._ring_size, self._ring_size)
        self.setAccessibleName("Session progress")
        self.setAccessibleDescription(
            "Circular indicator of elapsed session time."
        )

    @property
    def progress(self):
        """Elapsed fraction of the current phase, 0.0 … 1.0."""
        return self._progress

    def set_progress(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        value = max(0.0, min(1.0, value))
        # Tiny epsilon: two bindings reading the same paused clock
        # must converge on the exact same value (they can otherwise
        # keep float-identical-but-distinct readings), while a
        # running arc still repaints on every interpolation step.
        if abs(value - self._progress) < 1e-12:
            return
        self._progress = value
        self.update()

    def set_colors(self, track, arc):
        """Apply the theme-derived track/progress tones."""
        track_color = QColor(track)
        arc_color = QColor(arc)
        if track_color.isValid():
            self._track_color = track_color
        if arc_color.isValid():
            self._arc_color = arc_color
        self.update()

    @property
    def track_color(self):
        return self._track_color.name()

    @property
    def arc_color(self):
        return self._arc_color.name()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing, True
            )
            inset = self._pen_width // 2 + 2
            rect = self.rect().adjusted(inset, inset, -inset, -inset)
            pen = QPen(
                self._track_color,
                self._pen_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
            painter.setPen(pen)
            painter.drawArc(rect, 0, 360 * 16)
            if self._progress > 0:
                pen.setColor(self._arc_color)
                painter.setPen(pen)
                # Qt angles are 1/16 degree, positive counter-clockwise
                # from 3 o'clock: start at 12, sweep clockwise.
                span = -int(round(self._progress * 360 * 16))
                painter.drawArc(rect, 90 * 16, span)
        finally:
            painter.end()


class RingProgressBinding:
    """Display-only progress source for one ring, driven by one Clock.

    Subscribes to the clock's ``tick`` signal, so any view bound this
    way (main timer card, floating timer) stays synchronized with the
    same timer/session state — no second countdown exists anywhere.
    Between whole-second ticks the arc interpolates linearly from the
    last tick, so it glides instead of stepping; while the clock is
    paused/idle it mirrors the clock's exact remaining seconds, so
    pause, resume, skip and completion all freeze and resume both
    rings together.
    """

    INTERVAL_MS = 50

    def __init__(self, ring, clock, owner):
        """
        :param ring: the ``ProgressRing`` to drive.
        :param clock: the shared ``Clock``; may be ``None`` (view built
            without one, e.g. in isolation) — then the binding is inert.
        :param owner: QObject owning the interpolation timer (the view).
        """
        self._ring = ring
        self._clock = clock
        self._base_remaining = None
        self._base_time = 0.0
        self._timer = QTimer(owner)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self.sync)
        if clock is not None:
            clock.tick.connect(self._on_tick)

    # =====================================================
    # Lifecycle (owned by the view's show/hide events)
    # =====================================================

    @property
    def clock(self):
        """The shared Clock this ring mirrors (never owned here)."""
        return self._clock

    def start(self):
        """Anchor to the clock's current reading, then glide between ticks."""
        if self._clock is None:
            return
        self.rebase()
        self.sync()
        self._timer.start()

    def stop(self):
        """Stop gliding while the view is hidden; ticks still land."""
        self._timer.stop()

    @property
    def gliding(self):
        """True while the between-tick interpolation timer runs."""
        return self._timer.isActive()

    # =====================================================
    # Progress (the Clock stays the source of truth)
    # =====================================================

    def _on_tick(self, seconds):
        # Every tick (resets and phase changes emit one too) anchors
        # the between-tick interpolation to the shared clock's exact
        # reading, then refreshes the arc immediately.
        self.rebase(seconds)
        self.sync()

    def rebase(self, seconds=None):
        """Anchor the smooth ring interpolation to a fresh reading."""
        if seconds is None:
            seconds = getattr(self._clock, "remaining_seconds", 0) or 0
        self._base_remaining = float(max(0, int(seconds)))
        self._base_time = time.monotonic()

    def sync(self):
        """Update the ring from the shared clock; never owns state.

        The Clock only ticks once per second, so while it runs the
        remaining time is interpolated linearly from the last tick —
        the arc glides around the circumference instead of stepping.
        While paused/idle the ring mirrors the clock's exact remaining
        seconds, so pause/resume/skip/completion all stay in sync with
        the other view. No second countdown is started anywhere here.
        """
        clock = self._clock
        if clock is None:
            return
        total = getattr(clock, "total_seconds", 0) or 0
        if total <= 0:
            self._ring.set_progress(0.0)
            return

        if clock.is_running():
            if self._base_remaining is None:
                self.rebase()
            remaining = self._base_remaining - (
                time.monotonic() - self._base_time
            )
            remaining = max(
                0.0,
                min(self._base_remaining, remaining),
            )
        else:
            remaining = float(
                getattr(clock, "remaining_seconds", 0) or 0
            )
            # Keep the baseline fresh so resuming continues smoothly.
            self.rebase(int(remaining))

        progress = (total - remaining) / total
        self._ring.set_progress(max(0.0, min(1.0, progress)))
