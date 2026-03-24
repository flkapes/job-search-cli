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

    def get_attempt_by_id(self, attempt_id: int) -> dict | None:
        """Return a single attempt joined with its problem title."""
        return self.row_to_dict(
            self._execute_one(
                """SELECT pa.*, p.title AS problem_title
                   FROM problem_attempts pa
                   LEFT JOIN problems p ON pa.problem_id = p.id
                   WHERE pa.id = ?""",
                (attempt_id,),
            )
        )

    def get_attempts_for_session(self, session_id: int) -> list[dict]:
        """Return all attempts for a session, ordered by time."""
        return self.rows_to_dicts(
            self._execute(
                "SELECT * FROM problem_attempts WHERE session_id = ? ORDER BY attempted_at",
                (session_id,),
            )
        )

    def get_sessions_by_type(self, session_type: str) -> list[dict]:
        """Return all sessions of a given type."""
        return self.rows_to_dicts(
            self._execute(
                "SELECT * FROM practice_sessions WHERE session_type = ? ORDER BY started_at DESC",
                (session_type,),
            )
        )

    def set_difficulty_rating(self, attempt_id: int, rating: int) -> None:
        """Record the user's perceived difficulty for an attempt (1–5)."""
        if not (1 <= rating <= 5):
            raise ValueError(f"Difficulty rating must be 1–5, got {rating}")
        self._update(
            "UPDATE problem_attempts SET user_difficulty_rating = ? WHERE id = ?",
            (rating, attempt_id),
        )

    def get_mislabeled_problems(self, min_ratings: int = 3, divergence: float = 2.0) -> list[dict]:
        """
        Return problems where the average user rating diverges >= divergence steps
        from the label's numeric equivalent (easy=1, medium=3, hard=5), requiring
        at least min_ratings rated attempts.
        """
        return self.rows_to_dicts(
            self._execute(
                """SELECT p.id, p.title, p.difficulty,
                          COUNT(pa.user_difficulty_rating) AS rating_count,
                          AVG(pa.user_difficulty_rating)  AS avg_user_rating
                   FROM problems p
                   JOIN problem_attempts pa ON pa.problem_id = p.id
                   WHERE pa.user_difficulty_rating IS NOT NULL
                   GROUP BY p.id
                   HAVING rating_count >= ?
                      AND ABS(AVG(pa.user_difficulty_rating) -
                              CASE p.difficulty
                                  WHEN 'easy'   THEN 1.0
                                  WHEN 'medium' THEN 3.0
                                  WHEN 'hard'   THEN 5.0
                                  ELSE 3.0
                              END) >= ?""",
                (min_ratings, divergence),
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
