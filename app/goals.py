"""Canonical daily-goal store (Group 2).

``GoalManager`` is the single source of truth for daily focus targets.
Goals persist per calendar day (ISO ``YYYY-MM-DD``) in the ``daily_goals``
table created by the v2 migration. Values are validated at the boundary
(15–1440 minutes, default 120) so corrupt rows can never break the UI.

When the database is unavailable reads fall back to the default and
writes raise ``DatabaseError`` — callers that must never crash (timer,
history display) should read through ``GoalService`` instead, which adds
the QSettings mirror fallback.
"""

from datetime import date

from app.database import DatabaseError

DEFAULT_DAILY_GOAL_MINUTES = 120
MIN_DAILY_GOAL_MINUTES = 15
MAX_DAILY_GOAL_MINUTES = 1440


def clamp_goal_minutes(value, default=DEFAULT_DAILY_GOAL_MINUTES):
    """Clamp a goal value to the valid range, recovering to default."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(MIN_DAILY_GOAL_MINUTES, min(MAX_DAILY_GOAL_MINUTES, number))


def _today_iso():
    return date.today().isoformat()


class GoalManager:
    def __init__(self, database):
        self.database = database

    def get_daily_goal(self, day=None):
        """Return the target minutes for a day (today by default)."""
        if not self.database.is_available:
            return DEFAULT_DAILY_GOAL_MINUTES
        day = day or _today_iso()
        cursor = self.database.connection.cursor()
        cursor.execute(
            """
            SELECT target_minutes
            FROM daily_goals
            WHERE date = ?
            """,
            (day,),
        )
        result = cursor.fetchone()
        if not result:
            return DEFAULT_DAILY_GOAL_MINUTES
        return clamp_goal_minutes(result[0])

    def set_daily_goal(self, minutes, day=None):
        """Persist the target minutes for a day; returns the stored value."""
        if not self.database.is_available:
            raise DatabaseError(self.database.error_message)
        day = day or _today_iso()
        stored = clamp_goal_minutes(minutes)
        cursor = self.database.connection.cursor()
        cursor.execute(
            """
            INSERT INTO daily_goals (date, target_minutes)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET
                target_minutes = excluded.target_minutes,
                updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')
            """,
            (day, stored),
        )
        self.database.connection.commit()
        return stored

    def get_recent_goals(self, limit=30):
        """Return ``[(date, target_minutes), ...]`` newest first."""
        if not self.database.is_available:
            return []
        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 30
        cursor = self.database.connection.cursor()
        cursor.execute(
            """
            SELECT date, target_minutes
            FROM daily_goals
            ORDER BY date DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [(day, clamp_goal_minutes(target)) for day, target in rows]
