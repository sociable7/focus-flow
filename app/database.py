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
            self.ensure_schema_version()
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
                completed INTEGER NOT NULL DEFAULT 1,
                end_time TEXT,
                planned_seconds INTEGER,
                task_norm TEXT
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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_goals (
                date TEXT PRIMARY KEY,
                target_minutes INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%S', 'now')
                )
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_start_time
            ON sessions (start_time)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_task
            ON sessions (task)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_completed_type_time
            ON sessions (completed, session_type, start_time)
            """
        )

        # Fresh databases already have the v3 columns (see the sessions
        # DDL above). Older databases gain them via migrate_to_v3, which
        # also creates this index — so only create it here when the
        # column is already present.
        columns = {
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(sessions)"
            ).fetchall()
        }
        if "task_norm" in columns:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_task_norm
                ON sessions (task_norm)
                """
            )

        self.connection.commit()

    @staticmethod
    def normalize_task(task):
        """Normalized task key for grouping and filtering."""
        return (task or "").strip().lower()

    def add_session(
        self,
        task,
        start_time,
        duration_seconds,
        session_type="focus",
        completed=True,
        end_time=None,
        planned_seconds=None,
        task_norm=None,
    ):
        connection = self._require_connection()
        if task_norm is None:
            task_norm = self.normalize_task(task)
        if planned_seconds is None:
            planned_seconds = duration_seconds
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (
                    task,
                    start_time,
                    duration_seconds,
                    session_type,
                    completed,
                    end_time,
                    planned_seconds,
                    task_norm
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task,
                    start_time,
                    duration_seconds,
                    session_type,
                    int(completed),
                    end_time,
                    planned_seconds,
                    task_norm,
                ),
            )
            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            self._record_error("Saving a focus session failed", error)
            raise DatabaseError(self.error_message) from error

    def get_schema_version(self):
        """Return the stored schema version, or 0 when unavailable."""
        if self.connection is None:
            return 0
        from app.persistence.migrations import get_schema_version

        try:
            return get_schema_version(self.connection)
        except sqlite3.Error:
            return 0

    def ensure_schema_version(self):
        """Stamp the database at the current version (idempotent)."""
        from app.persistence.migrations import ensure_current

        return ensure_current(self)

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
