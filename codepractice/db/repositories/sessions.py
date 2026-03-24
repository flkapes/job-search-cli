"""Repository for practice sessions and attempts."""

from __future__ import annotations

from typing import Any

from codepractice.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository):

    def start_session(self, session_type: str = "free", plan_id: int | None = None) -> int:
        return self._insert(
            "INSERT INTO practice_sessions (session_type, plan_id) VALUES (?, ?)",
            (session_type, plan_id),
        )

    def end_session(self, session_id: int, total: int, solved: int, notes: str = "") -> None:
        self._update(
            """UPDATE practice_sessions
               SET ended_at = CURRENT_TIMESTAMP, total_problems = ?, solved_count = ?, notes = ?
               WHERE id = ?""",
            (total, solved, notes, session_id),
        )

    def get_session(self, session_id: int) -> dict | None:
        return self.row_to_dict(
            self._execute_one("SELECT * FROM practice_sessions WHERE id = ?", (session_id,))
        )

    def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        return self.rows_to_dicts(
            self._execute(
                "SELECT * FROM practice_sessions ORDER BY started_at DESC LIMIT ?", (limit,)
            )
        )

    def record_attempt(self, data: dict[str, Any]) -> int:
        return self._insert(
            """INSERT INTO problem_attempts
               (session_id, problem_id, user_code, user_explanation, ai_feedback,
                ai_score, time_spent_sec, hints_used, passed)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                data["session_id"],
                data["problem_id"],
                data.get("user_code", ""),
                data.get("user_explanation", ""),
                data.get("ai_feedback", ""),
                data.get("ai_score", 0.0),
                data.get("time_spent_sec", 0),
                data.get("hints_used", 0),
                1 if data.get("passed") else 0,
            ),
        )

    def get_attempts_for_category(self, category: str, limit: int = 20) -> list[dict]:
        return self.rows_to_dicts(
            self._execute(
                """SELECT pa.*, p.category, p.subcategory, p.difficulty
                   FROM problem_attempts pa
                   JOIN problems p ON pa.problem_id = p.id
                   WHERE p.category = ?
                   ORDER BY pa.attempted_at DESC
                   LIMIT ?""",
                (category, limit),
            )
        )

    def get_stats(self) -> dict[str, Any]:
        total_row = self._execute_one(
            "SELECT COUNT(*) as cnt, AVG(ai_score) as avg_score FROM problem_attempts"
        )
        solved_row = self._execute_one(
            "SELECT COUNT(*) as cnt FROM problem_attempts WHERE passed = 1"
        )
        streak_row = self._execute_one(
            """SELECT COUNT(DISTINCT DATE(attempted_at)) as days
               FROM problem_attempts
               WHERE attempted_at >= DATE('now', '-30 days')"""
        )
        today_row = self._execute_one(
            """SELECT COUNT(*) as cnt FROM problem_attempts
               WHERE DATE(attempted_at) = DATE('now')"""
        )
        return {
            "total_attempts": total_row["cnt"] if total_row else 0,
            "avg_score": round((total_row["avg_score"] or 0) * 100, 1) if total_row else 0,
            "total_solved": solved_row["cnt"] if solved_row else 0,
            "active_days_30": streak_row["days"] if streak_row else 0,
            "today_solved": today_row["cnt"] if today_row else 0,
        }

    def get_category_scores(self) -> list[dict]:
        return self.rows_to_dicts(
            self._execute(
                """SELECT p.category, p.subcategory,
                          COUNT(*) as attempts,
                          AVG(pa.ai_score) as avg_score,
                          SUM(pa.passed) as solved
                   FROM problem_attempts pa
                   JOIN problems p ON pa.problem_id = p.id
                   GROUP BY p.category, p.subcategory"""
            )
        )

    def get_daily_activity(self, days: int = 30) -> list[dict]:
        return self.rows_to_dicts(
            self._execute(
                """SELECT DATE(attempted_at) as day, COUNT(*) as count,
                          AVG(ai_score) as avg_score
                   FROM problem_attempts
                   WHERE attempted_at >= DATE('now', ? || ' days')
                   GROUP BY DATE(attempted_at)
                   ORDER BY day""",
                (f"-{days}",),
            )
        )
