"""Repository for problems table."""

from __future__ import annotations

import json
from typing import Any

from codepractice.db.repositories.base import BaseRepository


class ProblemRepository(BaseRepository):

    def create(self, data: dict[str, Any]) -> int:
        return self._insert(
            """INSERT INTO problems
               (source, category, subcategory, difficulty, title, description,
                constraints, examples_json, hints_json, solution_json, tags_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data.get("source", "static"),
                data["category"],
                data.get("subcategory", ""),
                data.get("difficulty", "medium"),
                data["title"],
                data["description"],
                data.get("constraints", ""),
                json.dumps(data.get("examples", [])),
                json.dumps(data.get("hints", [])),
                json.dumps(data.get("solution")) if data.get("solution") else None,
                json.dumps(data.get("tags", [])),
            ),
        )

    def get_by_id(self, problem_id: int) -> dict | None:
        row = self._execute_one("SELECT * FROM problems WHERE id = ?", (problem_id,))
        return self._parse_row(row)

    def get_by_category(
        self,
        category: str,
        subcategory: str | None = None,
        difficulty: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        conditions = ["category = ?"]
        params: list = [category]
        if subcategory:
            conditions.append("subcategory = ?")
            params.append(subcategory)
        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty)
        params.append(limit)
        sql = f"SELECT * FROM problems WHERE {' AND '.join(conditions)} ORDER BY RANDOM() LIMIT ?"
        rows = self._execute(sql, tuple(params))
        return [self._parse_row(r) for r in rows if r]

    def get_random(self, category: str | None = None, difficulty: str | None = None) -> dict | None:
        if category and difficulty:
            row = self._execute_one(
                "SELECT * FROM problems WHERE category=? AND difficulty=? ORDER BY RANDOM() LIMIT 1",
                (category, difficulty),
            )
        elif category:
            row = self._execute_one(
                "SELECT * FROM problems WHERE category=? ORDER BY RANDOM() LIMIT 1",
                (category,),
            )
        else:
            row = self._execute_one("SELECT * FROM problems ORDER BY RANDOM() LIMIT 1")
        return self._parse_row(row)

    def increment_shown(self, problem_id: int) -> None:
        self._update("UPDATE problems SET times_shown = times_shown + 1 WHERE id = ?", (problem_id,))

    def increment_solved(self, problem_id: int) -> None:
        self._update("UPDATE problems SET times_solved = times_solved + 1 WHERE id = ?", (problem_id,))

    def count_by_category(self) -> dict[str, int]:
        rows = self._execute("SELECT category, COUNT(*) as cnt FROM problems GROUP BY category")
        return {r["category"]: r["cnt"] for r in rows}

    def seed_if_empty(self, problems: list[dict]) -> int:
        existing = self._execute_one("SELECT COUNT(*) as cnt FROM problems")
        if existing and existing["cnt"] > 0:
            return 0
        count = 0
        for p in problems:
            self.create(p)
            count += 1
        return count

    @staticmethod
    def _parse_row(row) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        for field in ("examples_json", "hints_json", "solution_json", "tags_json"):
            raw = d.pop(field, None)
            key = field.replace("_json", "")
            try:
                d[key] = json.loads(raw) if raw else ([] if field != "solution_json" else None)
            except (json.JSONDecodeError, TypeError):
                d[key] = [] if field != "solution_json" else None
        return d
