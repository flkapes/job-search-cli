"""SQLite connection manager with automatic migration runner."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from codepractice.config import DB_PATH


class DatabaseManager:
    """Manages the SQLite connection and runs schema migrations."""

    MIGRATIONS_DIR = Path(__file__).parent / "migrations"

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_schema()

    # ── Connection management ──────────────────────────────────────────────────

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def get_connection(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Migration runner ───────────────────────────────────────────────────────

    def _ensure_schema(self) -> None:
        """Create migrations table and run any pending migrations."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    id          INTEGER PRIMARY KEY,
                    filename    TEXT UNIQUE NOT NULL,
                    applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        applied = self._get_applied_migrations()
        migration_files = sorted(self.MIGRATIONS_DIR.glob("*.sql"))

        for migration_file in migration_files:
            if migration_file.name not in applied:
                self._apply_migration(migration_file)

    def _get_applied_migrations(self) -> set[str]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT filename FROM _migrations").fetchall()
            return {row["filename"] for row in rows}

    def _apply_migration(self, migration_file: Path) -> None:
        sql = migration_file.read_text()
        with self.get_connection() as conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO _migrations (filename) VALUES (?)",
                (migration_file.name,),
            )


# Singleton instance
_db: DatabaseManager | None = None


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db
