"""Base repository with common CRUD operations."""

from __future__ import annotations

import sqlite3
from typing import Any

from codepractice.db.database import DatabaseManager


class BaseRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def _execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def _execute_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self.db.get_connection() as conn:
            return conn.execute(sql, params).fetchone()

    def _insert(self, sql: str, params: tuple = ()) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid

    def _update(self, sql: str, params: tuple = ()) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount

    @staticmethod
    def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(r) for r in rows]
