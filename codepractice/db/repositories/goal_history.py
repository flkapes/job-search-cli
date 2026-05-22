"""Repository for goal history and drift tracking."""

from __future__ import annotations

from codepractice.db.repositories.base import BaseRepository


class GoalHistoryRepository(BaseRepository):
    def create_entry(self, goal_text: str, plan_summary: str, plan_id: int | None = None) -> int:
        return self._insert(
            """INSERT INTO goal_history (plan_id, goal_text, plan_summary)
               VALUES (?, ?, ?)""",
            (plan_id, goal_text, plan_summary),
        )

    def list_recent(self, limit: int = 20) -> list[dict]:
        rows = self._execute(
            "SELECT * FROM goal_history ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return self.rows_to_dicts(rows)

    def list_for_plan(self, plan_id: int) -> list[dict]:
        rows = self._execute(
            "SELECT * FROM goal_history WHERE plan_id = ? ORDER BY created_at DESC, id DESC",
            (plan_id,),
        )
        return self.rows_to_dicts(rows)
