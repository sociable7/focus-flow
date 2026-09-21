"""Daily-goal service: database-canonical goals with a QSettings mirror.

Group 2 makes ``GoalManager`` (``daily_goals`` table) the single source
of truth. ``GoalService`` sits above it for UI code:

- reads prefer the database, falling back to the legacy QSettings value
  when the database is unavailable;
- writes go to the database first, then update the QSettings mirror so
  older reads (and a future reinstall without the DB file) keep working;
- ``import_from_settings()`` migrates a pre-Group-2 QSettings goal into
  the database exactly once (only when today has no stored goal);
- emits ``valueChanged("daily_goal_minutes")`` on every effective change
  so the main window can refresh without polling.
"""

from PySide6.QtCore import QObject, Signal

from datetime import date

from app.database import DatabaseError
from app.goals import DEFAULT_DAILY_GOAL_MINUTES, clamp_goal_minutes


class GoalService(QObject):
    valueChanged = Signal(str)

    def __init__(self, goals, settings):
        super().__init__()
        self.goals = goals
        self.settings = settings

    def get_daily_goal_minutes(self, day=None):
        """Return today's goal: DB first, QSettings mirror as fallback."""
        if self.goals.database.is_available:
            return self.goals.get_daily_goal(day)
        get = getattr(self.settings, "get_daily_goal_minutes", None)
        if callable(get):
            try:
                return clamp_goal_minutes(get())
            except DatabaseError:
                pass
        return DEFAULT_DAILY_GOAL_MINUTES

    def set_daily_goal_minutes(self, minutes, day=None):
        """Store the goal in the DB and mirror it to QSettings."""
        stored = self.goals.set_daily_goal(minutes, day)
        try:
            self.settings.set_daily_goal_minutes(stored)
        except (AttributeError, DatabaseError):
            pass
        self.valueChanged.emit("daily_goal_minutes")
        return stored

    def import_from_settings(self, day=None):
        """Migrate a legacy QSettings goal into the DB when today is empty.

        Returns True when a value was imported. Never overwrites an
        existing database row and never raises when the DB is down.
        """
        if not self.goals.database.is_available:
            return False
        get = getattr(self.settings, "get_daily_goal_minutes", None)
        if not callable(get):
            return False
        day = day or date.today().isoformat()
        cursor = self.goals.database.connection.cursor()
        cursor.execute(
            "SELECT 1 FROM daily_goals WHERE date = ?",
            (day,),
        )
        if cursor.fetchone():
            return False
        try:
            mirror = clamp_goal_minutes(get())
        except DatabaseError:
            return False
        if mirror == DEFAULT_DAILY_GOAL_MINUTES:
            return False
        try:
            self.goals.set_daily_goal(mirror, day)
        except DatabaseError:
            return False
        self.valueChanged.emit("daily_goal_minutes")
        return True
