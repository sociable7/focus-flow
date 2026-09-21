import logging
import sqlite3
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self, database):
        self.database = database

    # -------------------------------------------------
    # Add a completed focus session
    # -------------------------------------------------

    def add_focus_session(
        self,
        task,
        start_time,
        duration_seconds,
    ):
        """
        Save a completed focus session to the database.
        """

        self.database.add_session(
            task=task,
            start_time=start_time,
            duration_seconds=duration_seconds,
            session_type="focus",
            completed=True,
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

        today = datetime.now().date().isoformat()

        cursor = self._cursor()
        if cursor is None:
            return []

        cursor.execute(
            """
            SELECT
                task,
                start_time,
                duration_seconds
            FROM sessions
            WHERE session_type = 'focus'
            AND completed = 1
            AND date(start_time) = ?
            ORDER BY start_time DESC
            """,
            (today,),
        )

        return self._fetchall(cursor, [])

    # -------------------------------------------------
    # Get this week's focus sessions
    # -------------------------------------------------

    def get_this_week(self):
        """
        Return all completed focus sessions
        from the beginning of the current week.
        """

        today = datetime.now().date()

        start_of_week = today - timedelta(
            days=today.weekday()
        )

        cursor = self._cursor()
        if cursor is None:
            return []

        cursor.execute(
            """
            SELECT
                task,
                start_time,
                duration_seconds
            FROM sessions
            WHERE session_type = 'focus'
            AND completed = 1
            AND date(start_time) >= ?
            ORDER BY start_time DESC
            """,
            (start_of_week.isoformat(),),
        )

        return self._fetchall(cursor, [])

    # -------------------------------------------------
    # Get total focus time for a specific task
    # -------------------------------------------------

    def get_total_for_task(self, task):
        """
        Return the total completed focus time
        for a specific task in seconds.
        """

        cursor = self._cursor()
        if cursor is None:
            return 0

        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(duration_seconds),
                    0
                )
            FROM sessions
            WHERE task = ?
            AND session_type = 'focus'
            AND completed = 1
            """,
            (task,),
        )

        result = self._fetchone(cursor, (0,))
        return result[0]

    # -------------------------------------------------
    # Get today's total focus time
    # -------------------------------------------------

    def get_today_total(self):
        """
        Return today's total completed focus time
        in seconds.
        """

        today = datetime.now().date().isoformat()

        cursor = self._cursor()
        if cursor is None:
            return 0

        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(duration_seconds),
                    0
                )
            FROM sessions
            WHERE session_type = 'focus'
            AND completed = 1
            AND date(start_time) = ?
            """,
            (today,),
        )

        result = self._fetchone(cursor, (0,))
        return result[0]

    # -------------------------------------------------
    # Get total focus time for the current week
    # -------------------------------------------------

    def get_this_week_total(self):
        """
        Return this week's total completed focus time
        in seconds.
        """

        today = datetime.now().date()

        start_of_week = today - timedelta(
            days=today.weekday()
        )

        cursor = self._cursor()
        if cursor is None:
            return 0

        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(duration_seconds),
                    0
                )
            FROM sessions
            WHERE session_type = 'focus'
            AND completed = 1
            AND date(start_time) >= ?
            """,
            (start_of_week.isoformat(),),
        )

        result = self._fetchone(cursor, (0,))
        return result[0]

    # -------------------------------------------------
    # Get all unique tasks
    # -------------------------------------------------

    def get_tasks(self):
        """
        Return all unique tasks that have
        completed focus sessions.
        """

        cursor = self._cursor()
        if cursor is None:
            return []

        cursor.execute(
            """
            SELECT DISTINCT task
            FROM sessions
            WHERE session_type = 'focus'
            AND completed = 1
            ORDER BY task COLLATE NOCASE
            """
        )

        return [
            row[0]
            for row in self._fetchall(cursor, [])
        ]

    # -------------------------------------------------
    # Get all completed sessions
    # -------------------------------------------------

    def get_all(self):
        """
        Return all completed focus sessions.
        """

        cursor = self._cursor()
        if cursor is None:
            return []

        cursor.execute(
            """
            SELECT
                task,
                start_time,
                duration_seconds
            FROM sessions
            WHERE session_type = 'focus'
            AND completed = 1
            ORDER BY start_time DESC
            """
        )

        return self._fetchall(cursor, [])

    def _cursor(self):
        if not self.database.is_available:
            LOGGER.error(self.database.error_message)
            return None
        return self.database.connection.cursor()

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
