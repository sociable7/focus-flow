"""Backwards-compatible history facade over SessionRepository.

Group 2 moved every session query into
``app.persistence.session_repo.SessionRepository``. This class keeps the
original ``HistoryManager`` API (method names, argument and return
shapes) so existing UI and tests keep working unchanged. New code should
use ``SessionRepository`` directly.
"""

from app.persistence.session_repo import SessionRepository


class HistoryManager:
    def __init__(self, database):
        self.database = database
        self.sessions = SessionRepository(database)

    # -------------------------------------------------
    # Add a completed focus session
    # -------------------------------------------------

    def add_focus_session(
        self,
        task,
        start_time,
        duration_seconds,
        end_time=None,
        planned_seconds=None,
    ):
        """
        Save a completed focus session to the database.
        """

        self.sessions.add_focus_session(
            task=task,
            start_time=start_time,
            duration_seconds=duration_seconds,
            end_time=end_time,
            planned_seconds=planned_seconds,
        )

    # -------------------------------------------------
    # Get today's focus sessions
    # -------------------------------------------------

    def get_today(self):
        """
        Return all completed focus sessions from today.

        Returns:
            list of tuples:
            (
                task,
                start_time,
                duration_seconds
            )
        """

        return self.sessions.get_today()

    # -------------------------------------------------
    # Get this week's focus sessions
    # -------------------------------------------------

    def get_this_week(self):
        """
        Return all completed focus sessions
        from the beginning of the current week.
        """

        return self.sessions.get_this_week()

    # -------------------------------------------------
    # Get total focus time for a specific task
    # -------------------------------------------------

    def get_total_for_task(self, task):
        """
        Return the total completed focus time
        for a specific task in seconds.
        """

        return self.sessions.total_for_task(task)

    # -------------------------------------------------
    # Get today's total focus time
    # -------------------------------------------------

    def get_today_total(self):
        """
        Return today's total completed focus time
        in seconds.
        """

        return self.sessions.today_total()

    # -------------------------------------------------
    # Get total focus time for the current week
    # -------------------------------------------------

    def get_this_week_total(self):
        """
        Return this week's total completed focus time
        in seconds.
        """

        return self.sessions.week_total()

    # -------------------------------------------------
    # Get all unique tasks
    # -------------------------------------------------

    def get_tasks(self):
        """
        Return all unique tasks that have
        completed focus sessions.
        """

        return self.sessions.tasks()

    # -------------------------------------------------
    # Get all completed sessions
    # -------------------------------------------------

    def get_all(self):
        """
        Return all completed focus sessions.
        """

        return self.sessions.get_all()

    # -------------------------------------------------
    # Get recent sessions (paged)
    # -------------------------------------------------

    def get_recent_sessions(self, limit=50):
        """
        Return the most recent completed focus sessions,
        newest first, capped at ``limit`` rows.
        """

        return self.sessions.get_recent(limit)

    # -------------------------------------------------
    # Get lifetime total focus time
    # -------------------------------------------------

    def get_total(self):
        """
        Return the lifetime total completed focus time
        in seconds (avoids loading every session row).
        """

        return self.sessions.lifetime_total()

    # -------------------------------------------------
    # Get lifetime completed session count
    # -------------------------------------------------

    def get_session_count(self):
        """
        Return the number of completed focus sessions.
        """

        return self.sessions.session_count()

    # -------------------------------------------------
    # Get per-day totals for the last N days
    # -------------------------------------------------

    def get_daily_totals(self, days=7):
        """
        Return ``[(date_iso, seconds), ...]`` for the last ``days``
        calendar days including today, oldest first. Days without
        sessions report 0 seconds.
        """

        return self.sessions.daily_series(days)

    # -------------------------------------------------
    # Get current daily streak
    # -------------------------------------------------

    def get_day_streak(self):
        """
        Return the number of consecutive calendar days with at
        least one completed focus session, counting back from
        today (a missing today still counts when yesterday
        completed — the streak is only broken by a full miss).
        """

        return self.sessions.day_streak()

    # -------------------------------------------------
    # Get per-task breakdown
    # -------------------------------------------------

    def get_task_breakdown(self, limit=5):
        """
        Return ``[(task, seconds, sessions), ...]`` ordered by
        total focus time descending, capped at ``limit`` tasks.
        """

        return self.sessions.per_task(limit)
