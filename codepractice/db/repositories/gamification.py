"""Repository for XP events and achievement unlocks."""

from __future__ import annotations

from codepractice.db.repositories.base import BaseRepository


class GamificationRepository(BaseRepository):

    # ── XP ─────────────────────────────────────────────────────────────────────

    def add_xp(
        self,
        xp: int,
        reason: str = "",
        attempt_id: int | None = None,
        problem_id: int | None = None,
    ) -> int:
        return self._insert(
            "INSERT INTO xp_events (attempt_id, problem_id, xp, reason) VALUES (?,?,?,?)",
            (attempt_id, problem_id, xp, reason),
        )

    def total_xp(self) -> int:
        row = self._execute_one("SELECT COALESCE(SUM(xp), 0) AS total FROM xp_events")
        return int(row["total"]) if row else 0

    def xp_by_day(self, days: int = 30) -> list[dict]:
        return self.rows_to_dicts(
            self._execute(
                """SELECT DATE(created_at) AS day, SUM(xp) AS xp
                   FROM xp_events
                   WHERE created_at >= DATE('now', ? || ' days')
                   GROUP BY DATE(created_at)
                   ORDER BY day""",
                (f"-{days}",),
            )
        )

    # ── Achievements ───────────────────────────────────────────────────────────

    def unlocked_keys(self) -> set[str]:
        rows = self._execute("SELECT key FROM achievements")
        return {r["key"] for r in rows}

    def unlock(self, key: str) -> bool:
        """Unlock an achievement. Returns True if newly unlocked."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO achievements (key) VALUES (?)", (key,)
            )
            return cursor.rowcount > 0

    def unlocked_with_dates(self) -> list[dict]:
        return self.rows_to_dicts(
            self._execute("SELECT key, unlocked_at FROM achievements ORDER BY unlocked_at")
        )

    # ── Achievement context queries ────────────────────────────────────────────

    def solved_dsa_pattern_count(self) -> int:
        row = self._execute_one(
            """SELECT COUNT(DISTINCT p.subcategory) AS cnt
               FROM problem_attempts pa
               JOIN problems p ON p.id = pa.problem_id
               WHERE pa.passed = 1 AND p.category = 'dsa' AND p.subcategory != ''"""
        )
        return int(row["cnt"]) if row else 0

    def solved_count_for_category(self, category: str) -> int:
        row = self._execute_one(
            """SELECT COUNT(*) AS cnt
               FROM problem_attempts pa
               JOIN problems p ON p.id = pa.problem_id
               WHERE pa.passed = 1 AND p.category = ?""",
            (category,),
        )
        return int(row["cnt"]) if row else 0

    def no_hint_solve_count(self) -> int:
        row = self._execute_one(
            "SELECT COUNT(*) AS cnt FROM problem_attempts WHERE passed = 1 AND hints_used = 0"
        )
        return int(row["cnt"]) if row else 0

    def has_prior_failed_attempt(self, problem_id: int, before_attempt_id: int) -> bool:
        row = self._execute_one(
            """SELECT COUNT(*) AS cnt FROM problem_attempts
               WHERE problem_id = ? AND passed = 0 AND id < ?""",
            (problem_id, before_attempt_id),
        )
        return bool(row and row["cnt"] > 0)

    def languages_solved_count(self) -> int:
        row = self._execute_one(
            """SELECT COUNT(DISTINCT COALESCE(language, 'python')) AS cnt
               FROM problem_attempts WHERE passed = 1"""
        )
        return int(row["cnt"]) if row else 0

    def bookmark_count(self) -> int:
        row = self._execute_one(
            "SELECT COUNT(*) AS cnt FROM problems WHERE bookmarked_at IS NOT NULL"
        )
        return int(row["cnt"]) if row else 0

    def custom_problem_count(self) -> int:
        row = self._execute_one(
            "SELECT COUNT(*) AS cnt FROM problems WHERE source = 'custom'"
        )
        return int(row["cnt"]) if row else 0

    def any_plan_completed(self) -> bool:
        row = self._execute_one(
            "SELECT COUNT(*) AS cnt FROM learning_plans WHERE status = 'completed'"
        )
        return bool(row and row["cnt"] > 0)

    def any_simulation_passed(self) -> bool:
        """A simulation counts as passed when its recorded avg score is >= 0.7."""
        row = self._execute_one(
            """SELECT COUNT(*) AS cnt
               FROM practice_sessions ps
               WHERE ps.session_type = 'interview_simulation'
                 AND ps.ended_at IS NOT NULL
                 AND (SELECT AVG(pa.ai_score) FROM problem_attempts pa
                      WHERE pa.session_id = ps.id) >= 0.7"""
        )
        return bool(row and row["cnt"] > 0)
