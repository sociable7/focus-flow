import logging
import sqlite3

LOGGER = logging.getLogger(__name__)

#: Current schema version. v1 covers the original prototype tables plus
#: the ``schema_version`` bookkeeping table itself. v2 adds the canonical
#: ``daily_goals`` table and indexes over ``sessions``. v3 adds
#: ``end_time``, ``planned_seconds`` and ``task_norm`` columns to
#: ``sessions`` (backfilled for existing rows) plus a ``task_norm`` index.
CURRENT_VERSION = 3


def get_schema_version(connection):
    """Return the stored schema version, or 0 for legacy databases."""
    try:
        row = connection.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return 0
    if not row:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


def migrate_to_v2(connection):
    """Bring a v1 database up to v2 (idempotent, preserves user data).

    - Creates the canonical ``daily_goals`` table.
    - Migrates legacy ``goals`` rows (``goal_type='daily'``) into it,
      keeping the largest target per date and stamping ``updated_at``
      from the current time.
    - Creates indexes over ``sessions`` used by the history queries.
    """
    connection.execute(
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
    try:
        rows = connection.execute(
            """
            SELECT date, MAX(target_minutes)
            FROM goals
            WHERE goal_type = 'daily'
            GROUP BY date
            """
        ).fetchall()
    except sqlite3.Error:
        rows = []
    for day, target in rows:
        if day is None:
            continue
        try:
            minutes = int(target)
        except (TypeError, ValueError):
            continue
        connection.execute(
            """
            INSERT INTO daily_goals (date, target_minutes)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET
                target_minutes = excluded.target_minutes
            WHERE excluded.target_minutes
                > daily_goals.target_minutes
            """,
            (day, minutes),
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_start_time
        ON sessions (start_time)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_task
        ON sessions (task)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_completed_type_time
        ON sessions (completed, session_type, start_time)
        """
    )
    connection.commit()


def _session_columns(connection):
    """Return the set of existing ``sessions`` column names."""
    try:
        rows = connection.execute("PRAGMA table_info(sessions)").fetchall()
    except sqlite3.Error:
        return set()
    return {row[1] for row in rows if len(row) > 1}


def migrate_to_v3(connection):
    """Bring a v2 database up to v3 (idempotent, preserves user data).

    - Adds ``end_time`` (ISO timestamp, nullable), ``planned_seconds``
      and ``task_norm`` (lowercased task for grouping/filtering).
    - Backfills existing rows: ``task_norm`` from ``task``,
      ``planned_seconds`` from ``duration_seconds``.
    - Creates an index over ``task_norm``.
    """
    existing = _session_columns(connection)
    if "end_time" not in existing:
        connection.execute(
            "ALTER TABLE sessions ADD COLUMN end_time TEXT"
        )
    if "planned_seconds" not in existing:
        connection.execute(
            "ALTER TABLE sessions ADD COLUMN planned_seconds INTEGER"
        )
    if "task_norm" not in existing:
        connection.execute(
            "ALTER TABLE sessions ADD COLUMN task_norm TEXT"
        )
    connection.execute(
        """
        UPDATE sessions
        SET task_norm = lower(trim(task))
        WHERE task_norm IS NULL
        """
    )
    connection.execute(
        """
        UPDATE sessions
        SET planned_seconds = duration_seconds
        WHERE planned_seconds IS NULL
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_task_norm
        ON sessions (task_norm)
        """
    )
    connection.commit()


def ensure_current(database):
    """Migrate the database to the current version.

    Idempotent and safe to call on every open. Legacy databases without
    a ``schema_version`` table are stamped at v1 first, then stepped to
    the current version without touching user sessions or goals.
    """
    if not database.is_available:
        return False
    connection = database.connection
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%S', 'now')
                )
            )
            """
        )
        connection.commit()
        if get_schema_version(connection) < 1:
            connection.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (1,),
            )
            connection.commit()
        if get_schema_version(connection) < 2:
            migrate_to_v2(connection)
            connection.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (2,),
            )
            connection.commit()
        if get_schema_version(connection) < 3:
            migrate_to_v3(connection)
            connection.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (3,),
            )
            connection.commit()
        return True
    except sqlite3.Error:
        LOGGER.exception("Stamping schema version failed")
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
        return False
