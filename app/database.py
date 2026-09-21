import logging
import sqlite3
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """A database operation failed and the session could not be persisted."""


class Database:
    def __init__(self, app_data_dir=None):
        self.app_data_dir = Path(app_data_dir) if app_data_dir else (
            Path.home() / "Library" / "Application Support" / "Focus Flow"
        )
        self.db_path = self.app_data_dir / "focus_flow.db"
        self.connection = None
        self.error_message = ""

        try:
            self.app_data_dir.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.db_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.create_tables()
        except (OSError, sqlite3.Error) as error:
            self._record_error("Database initialization failed", error)
            self.close()

    @property
    def is_available(self):
        return self.connection is not None

    def _record_error(self, context, error):
        self.error_message = f"{context}: {error}"
        LOGGER.exception(self.error_message)

    def _require_connection(self):
        if self.connection is None:
            raise DatabaseError(
                self.error_message or "Focus Flow's database is unavailable."
            )
        return self.connection

    def create_tables(self):
        cursor = self._require_connection().cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                session_type TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL,
                target_minutes INTEGER NOT NULL,
                date TEXT NOT NULL
            )
            """
        )

        self.connection.commit()

    def add_session(
        self,
        task,
        start_time,
        duration_seconds,
        session_type="focus",
        completed=True,
    ):
        connection = self._require_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (
                    task,
                    start_time,
                    duration_seconds,
                    session_type,
                    completed
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task,
                    start_time,
                    duration_seconds,
                    session_type,
                    int(completed),
                ),
            )
            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            self._record_error("Saving a focus session failed", error)
            raise DatabaseError(self.error_message) from error

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
