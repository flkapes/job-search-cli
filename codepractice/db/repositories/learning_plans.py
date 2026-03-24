"""Repository for learning plans."""

from __future__ import annotations

import json
from typing import Any

from codepractice.db.repositories.base import BaseRepository


class LearningPlanRepository(BaseRepository):

    def create(self, data: dict[str, Any]) -> int:
        return self._insert(
            """INSERT INTO learning_plans
               (title, natural_language_goal, duration_days, plan_json)
               VALUES (?,?,?,?)""",
            (
                data["title"],
                data.get("natural_language_goal", ""),
                data.get("duration_days", 30),
                json.dumps(data.get("plan", {})),
            ),
        )

    def get_active(self) -> dict | None:
        row = self._execute_one(
            "SELECT * FROM learning_plans WHERE status = 'active' ORDER BY created_at DESC LIMIT 1"
        )
        return self._parse(row)

    def get_by_id(self, plan_id: int) -> dict | None:
        row = self._execute_one("SELECT * FROM learning_plans WHERE id = ?", (plan_id,))
        return self._parse(row)

    def list_all(self) -> list[dict]:
        rows = self._execute("SELECT * FROM learning_plans ORDER BY created_at DESC")
        return [self._parse(r) for r in rows if r]

    def update_status(self, plan_id: int, status: str) -> None:
        self._update(
            "UPDATE learning_plans SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, plan_id),
        )

    def advance_day(self, plan_id: int) -> None:
        self._update(
            """UPDATE learning_plans
               SET current_day = current_day + 1, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (plan_id,),
        )

    def update_plan_json(self, plan_id: int, plan: dict) -> None:
        self._update(
            "UPDATE learning_plans SET plan_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(plan), plan_id),
        )

    def add_day(self, plan_id: int, day_data: dict) -> int:
        return self._insert(
            """INSERT INTO plan_days
               (plan_id, day_number, theme, objectives_json, problem_ids_json, estimated_minutes)
               VALUES (?,?,?,?,?,?)""",
            (
                plan_id,
                day_data["day_number"],
                day_data.get("theme", ""),
                json.dumps(day_data.get("objectives", [])),
                json.dumps(day_data.get("problem_ids", [])),
                day_data.get("estimated_minutes", 45),
            ),
        )

    def get_days(self, plan_id: int) -> list[dict]:
        rows = self._execute(
            "SELECT * FROM plan_days WHERE plan_id = ? ORDER BY day_number", (plan_id,)
        )
        return [self._parse_day(r) for r in rows]

    def complete_day(self, day_id: int, notes: str = "") -> None:
        self._update(
            "UPDATE plan_days SET completed = 1, completed_at = CURRENT_TIMESTAMP, notes = ? WHERE id = ?",
            (notes, day_id),
        )

    @staticmethod
    def _parse(row) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        try:
            d["plan"] = json.loads(d.pop("plan_json", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["plan"] = {}
        return d

    @staticmethod
    def _parse_day(row) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        for field in ("objectives_json", "problem_ids_json"):
            raw = d.pop(field, "[]")
            key = field.replace("_json", "")
            try:
                d[key] = json.loads(raw or "[]")
            except (json.JSONDecodeError, TypeError):
                d[key] = []
        return d
