from datetime import date

from app.database import DatabaseError


class GoalManager:
    def __init__(self, database):
        self.database = database

    def set_daily_goal(self, minutes):
        if not self.database.is_available:
            raise DatabaseError(self.database.error_message)

        today = date.today().isoformat()

        cursor = self.database.connection.cursor()

        cursor.execute(
            """
            DELETE FROM goals
            WHERE goal_type = 'daily'
            AND date = ?
            """,
            (today,),
        )

        cursor.execute(
            """
            INSERT INTO goals (
                goal_type,
                target_minutes,
                date
            )
            VALUES (?, ?, ?)
            """,
            (
                "daily",
                minutes,
                today,
            ),
        )

        self.database.connection.commit()

    def get_daily_goal(self):
        if not self.database.is_available:
            return 120

        today = date.today().isoformat()

        cursor = self.database.connection.cursor()

        cursor.execute(
            """
            SELECT target_minutes
            FROM goals
            WHERE goal_type = 'daily'
            AND date = ?
            """,
            (today,),
        )

        result = cursor.fetchone()

        if result:
            return result[0]

        return 120
