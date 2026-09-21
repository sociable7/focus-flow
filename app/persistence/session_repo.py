"""Session repository: all SQLite access for focus sessions.

Group 2 moves every session query out of UI and manager classes into
this repository. All aggregates run in SQL (no full-table loads into
Python) and every read degrades to a safe default when the database is
unavailable or a query fails — the timer must never crash because
history is broken. Repository code knows nothing about widgets.

Write path (``add_focus_session``) raises ``DatabaseError`` on failure
so callers can warn while letting the timer continue.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)

FOCUS_FILTER = "session_type = 'focus' AND completed = 1"


def _clamp_int(value, default, minimum, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


class SessionRepository:
    def __init__(self, database):
        self.database = database

    # =====================================================
    # Writes
    # =====================================================

    def add_focus_session(
        self,
        task,
        start_time,
        duration_seconds,
        end_time=None,
        planned_seconds=None,
    ):
        """Persist one completed focus session."""
        self.database.add_session(
            task=task,
            start_time=start_time,
            duration_seconds=duration_seconds,
            session_type="focus",
            completed=True,
            end_time=end_time,
            planned_seconds=(
                duration_seconds
                if planned_seconds is None
                else planned_seconds
            ),
        )

    # =====================================================
    # Internal helpers
    # =====================================================

    def _cursor(self):
        if not self.database.is_available:
            LOGGER.error(self.database.error_message)
            return None
        try:
            return self.database.connection.cursor()
        except sqlite3.Error:
            LOGGER.exception("Opening a history cursor failed")
            return None

    @staticmethod
    def _fetchall(cursor, default):
        try:
            return cursor.fetchall()
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return default

    @staticmethod
    def _fetchone(cursor, default):
        try:
            return cursor.fetchone() or default
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return default

    def _total_where(self, extra="", params=()):
        cursor = self._cursor()
        if cursor is None:
            return 0
        try:
            cursor.execute(
                f"""
                SELECT COALESCE(SUM(duration_seconds), 0)
                FROM sessions
                WHERE {FOCUS_FILTER} {extra}
                """,
                params,
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return 0
        return self._fetchone(cursor, (0,))[0]

    # =====================================================
    # Totals
    # =====================================================

    def today_total(self):
        today = datetime.now().date().isoformat()
        return self._total_where(
            "AND date(start_time) = ?", (today,)
        )

    def week_total(self):
        today = datetime.now().date()
        start = today - timedelta(days=today.weekday())
        return self._total_where(
            "AND date(start_time) >= ?", (start.isoformat(),)
        )

    def lifetime_total(self):
        return self._total_where()

    def session_count(self):
        cursor = self._cursor()
        if cursor is None:
            return 0
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM sessions
                WHERE {FOCUS_FILTER}
                """
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return 0
        return self._fetchone(cursor, (0,))[0]

    def total_for_task(self, task):
        from app.database import Database

        cursor = self._cursor()
        if cursor is None:
            return 0
        try:
            cursor.execute(
                f"""
                SELECT COALESCE(SUM(duration_seconds), 0)
                FROM sessions
                WHERE {FOCUS_FILTER}
                AND task_norm = ?
                """,
                (Database.normalize_task(task),),
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return 0
        return self._fetchone(cursor, (0,))[0]

    # =====================================================
    # Series / breakdowns
    # =====================================================

    def daily_series(self, days=7):
        """``[(date_iso, seconds), ...]`` oldest first, zero-filled."""
        days = _clamp_int(days, 7, 1)
        today = datetime.now().date()
        start = today - timedelta(days=days - 1)
        totals = {
            (start + timedelta(days=offset)).isoformat(): 0
            for offset in range(days)
        }
        cursor = self._cursor()
        if cursor is None:
            return sorted(totals.items())
        try:
            cursor.execute(
                f"""
                SELECT date(start_time),
                       COALESCE(SUM(duration_seconds), 0)
                FROM sessions
                WHERE {FOCUS_FILTER}
                AND date(start_time) >= ?
                GROUP BY date(start_time)
                """,
                (start.isoformat(),),
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return sorted(totals.items())
        for day, seconds in self._fetchall(cursor, []):
            if day in totals:
                totals[day] = seconds
        return sorted(totals.items())

    def per_task(self, limit=5):
        """``[(display_task, seconds, sessions), ...]`` by time desc."""
        limit = _clamp_int(limit, 5, 1)
        cursor = self._cursor()
        if cursor is None:
            return []
        try:
            cursor.execute(
                f"""
                SELECT (
                        SELECT s2.task
                        FROM sessions s2
                        WHERE s2.task_norm = agg.task_norm
                        ORDER BY s2.start_time DESC, s2.rowid DESC
                        LIMIT 1
                    ),
                    agg.seconds,
                    agg.sessions
                FROM (
                    SELECT task_norm,
                           COALESCE(SUM(duration_seconds), 0) AS seconds,
                           COUNT(*) AS sessions
                    FROM sessions
                    WHERE {FOCUS_FILTER}
                    GROUP BY task_norm
                ) AS agg
                ORDER BY agg.seconds DESC
                LIMIT ?
                """,
                (limit,),
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return []
        return self._fetchall(cursor, [])

    def tasks(self):
        """Distinct task display names, most recently used first."""
        cursor = self._cursor()
        if cursor is None:
            return []
        try:
            cursor.execute(
                f"""
                SELECT task
                FROM sessions
                WHERE {FOCUS_FILTER}
                GROUP BY task_norm
                ORDER BY MAX(start_time) DESC
                """
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return []
        return [row[0] for row in self._fetchall(cursor, [])]

    def day_streak(self):
        """Consecutive active days back from today (or yesterday)."""
        cursor = self._cursor()
        if cursor is None:
            return 0
        try:
            cursor.execute(
                f"""
                SELECT DISTINCT date(start_time)
                FROM sessions
                WHERE {FOCUS_FILTER}
                ORDER BY date(start_time) DESC
                """
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return 0
        active = {row[0] for row in self._fetchall(cursor, [])}
        expected = datetime.now().date()
        if expected.isoformat() not in active:
            expected -= timedelta(days=1)
        streak = 0
        while expected.isoformat() in active:
            streak += 1
            expected -= timedelta(days=1)
        return streak

    # =====================================================
    # Listings
    # =====================================================

    def page(
        self,
        limit=50,
        offset=0,
        task_query=None,
        date_from=None,
        date_to=None,
    ):
        """Newest-first ``(task, start_time, duration)`` rows.

        ``task_query`` matches case-insensitively via ``task_norm``;
        ``date_from``/``date_to`` are ISO ``YYYY-MM-DD`` bounds applied
        to ``date(start_time)`` (inclusive).
        """
        from app.database import Database

        limit = _clamp_int(limit, 50, 1)
        offset = _clamp_int(offset, 0, 0)
        clauses = []
        params = []
        if task_query and str(task_query).strip():
            norm = Database.normalize_task(task_query)
            escaped = (
                norm.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            clauses.append("AND task_norm LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        if date_from:
            clauses.append("AND date(start_time) >= ?")
            params.append(str(date_from))
        if date_to:
            clauses.append("AND date(start_time) <= ?")
            params.append(str(date_to))
        extra = " ".join(clauses)
        params.extend([limit, offset])

        cursor = self._cursor()
        if cursor is None:
            return []
        try:
            cursor.execute(
                f"""
                SELECT task, start_time, duration_seconds
                FROM sessions
                WHERE {FOCUS_FILTER} {extra}
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params),
            )
        except sqlite3.Error:
            LOGGER.exception("Reading focus history failed")
            return []
        return self._fetchall(cursor, [])

    # =====================================================
    # Backwards-compatible listings
    # =====================================================

    def get_today(self):
        today = datetime.now().date().isoformat()
        return self.page(limit=1000000, date_from=today, date_to=today)

    def get_this_week(self):
        today = datetime.now().date()
        start = today - timedelta(days=today.weekday())
        return self.page(limit=1000000, date_from=start.isoformat())

    def get_all(self):
        return self.page(limit=1000000)

    def get_recent(self, limit=50):
        return self.page(limit=limit)
