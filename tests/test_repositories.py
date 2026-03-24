"""Tests for SQLite repository layer (uses tmp_db fixture)."""

from __future__ import annotations

import pytest

from codepractice.db.repositories.problems import ProblemRepository
from codepractice.db.repositories.sessions import SessionRepository
from codepractice.db.repositories.profile import ProfileRepository


# ── Helpers ────────────────────────────────────────────────────────────────────

def _problem_data(**overrides) -> dict:
    base = {
        "source": "static",
        "category": "dsa",
        "subcategory": "two_pointers",
        "difficulty": "easy",
        "title": "Two Sum",
        "description": "Return indices of two numbers that add to target.",
        "constraints": "2 <= n <= 100",
        "examples": [{"input": "[2,7,11,15], 9", "output": "[0,1]", "explanation": "2+7=9"}],
        "hints": ["Use a hash map"],
        "tags": ["array"],
    }
    base.update(overrides)
    return base


# ── ProblemRepository ──────────────────────────────────────────────────────────

class TestProblemRepository:
    def test_create_and_get_by_id(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create(_problem_data())
        assert isinstance(pid, int)
        assert pid > 0

        row = repo.get_by_id(pid)
        assert row is not None
        assert row["title"] == "Two Sum"
        assert row["category"] == "dsa"
        assert row["difficulty"] == "easy"

    def test_get_by_id_missing_returns_none(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        assert repo.get_by_id(99999) is None

    def test_json_fields_parsed(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create(_problem_data())
        row = repo.get_by_id(pid)
        assert isinstance(row["examples"], list)
        assert isinstance(row["hints"], list)
        assert isinstance(row["tags"], list)
        assert row["hints"] == ["Use a hash map"]

    def test_get_by_category(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        repo.create(_problem_data(category="dsa", subcategory="bfs", difficulty="medium"))
        repo.create(_problem_data(category="dsa", subcategory="bfs", title="Level Order"))
        repo.create(_problem_data(category="python_fundamentals", title="Decorators"))

        dsa = repo.get_by_category("dsa")
        assert len(dsa) == 2
        assert all(p["category"] == "dsa" for p in dsa)

    def test_get_by_category_with_filters(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        repo.create(_problem_data(subcategory="bfs", difficulty="medium", title="BFS easy"))
        repo.create(_problem_data(subcategory="bfs", difficulty="hard", title="BFS hard"))

        result = repo.get_by_category("dsa", subcategory="bfs", difficulty="medium")
        assert len(result) == 1
        assert result[0]["title"] == "BFS easy"

    def test_get_random_returns_problem(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        repo.create(_problem_data())
        result = repo.get_random()
        assert result is not None
        assert result["title"] == "Two Sum"

    def test_get_random_empty_returns_none(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        assert repo.get_random() is None

    def test_increment_shown(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create(_problem_data())
        repo.increment_shown(pid)
        repo.increment_shown(pid)
        row = repo.get_by_id(pid)
        assert row["times_shown"] == 2

    def test_increment_solved(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create(_problem_data())
        repo.increment_solved(pid)
        row = repo.get_by_id(pid)
        assert row["times_solved"] == 1

    def test_count_by_category(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        repo.create(_problem_data(category="dsa"))
        repo.create(_problem_data(category="dsa", title="P2"))
        repo.create(_problem_data(category="python_fundamentals", title="P3"))

        counts = repo.count_by_category()
        assert counts.get("dsa") == 2
        assert counts.get("python_fundamentals") == 1

    def test_seed_if_empty_seeds_once(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        problems = [_problem_data(title=f"P{i}") for i in range(3)]
        seeded = repo.seed_if_empty(problems)
        assert seeded == 3
        # Second call should be a no-op
        seeded2 = repo.seed_if_empty(problems)
        assert seeded2 == 0


# ── SessionRepository ──────────────────────────────────────────────────────────

class TestSessionRepository:
    def test_start_and_get_session(self, tmp_db):
        repo = SessionRepository(tmp_db)
        sid = repo.start_session("free")
        assert isinstance(sid, int)
        session = repo.get_session(sid)
        assert session is not None
        assert session["session_type"] == "free"

    def test_end_session(self, tmp_db):
        repo = SessionRepository(tmp_db)
        sid = repo.start_session("dsa")
        repo.end_session(sid, total=5, solved=3)
        session = repo.get_session(sid)
        assert session["total_problems"] == 5
        assert session["solved_count"] == 3

    def test_record_attempt(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        repo = SessionRepository(tmp_db)
        pid = prob_repo.create(_problem_data())
        sid = repo.start_session("free")

        attempt_id = repo.record_attempt({
            "session_id": sid,
            "problem_id": pid,
            "user_code": "def two_sum(): pass",
            "ai_feedback": "Needs improvement",
            "ai_score": 0.75,
            "time_spent_sec": 120,
            "hints_used": 1,
            "passed": True,
        })
        assert isinstance(attempt_id, int)

    def test_get_stats_empty(self, tmp_db):
        repo = SessionRepository(tmp_db)
        stats = repo.get_stats()
        assert stats["total_attempts"] == 0
        assert stats["total_solved"] == 0

    def test_get_stats_with_data(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        repo = SessionRepository(tmp_db)
        pid = prob_repo.create(_problem_data())
        sid = repo.start_session("free")
        repo.record_attempt({
            "session_id": sid, "problem_id": pid,
            "ai_score": 0.8, "passed": True,
        })
        repo.record_attempt({
            "session_id": sid, "problem_id": pid,
            "ai_score": 0.4, "passed": False,
        })
        stats = repo.get_stats()
        assert stats["total_attempts"] == 2
        assert stats["total_solved"] == 1

    def test_get_recent_sessions(self, tmp_db):
        repo = SessionRepository(tmp_db)
        for _ in range(3):
            repo.start_session("free")
        sessions = repo.get_recent_sessions(limit=2)
        assert len(sessions) == 2


# ── ProfileRepository ──────────────────────────────────────────────────────────

class TestProfileRepository:
    def test_create_and_get(self, tmp_db):
        repo = ProfileRepository(tmp_db)
        assert not repo.exists()
        repo.create({
            "name": "Alice",
            "target_role": "SWE",
            "experience_level": "senior",
            "llm_backend": "ollama",
            "llm_model": "llama3",
        })
        assert repo.exists()
        profile = repo.get()
        assert profile is not None
        assert profile["name"] == "Alice"
        assert profile["experience_level"] == "senior"

    def test_update_fields(self, tmp_db):
        repo = ProfileRepository(tmp_db)
        repo.create({"name": "Bob", "llm_model": "llama3"})
        repo.update({"name": "Bobby", "llm_model": "codellama"})
        profile = repo.get()
        assert profile["name"] == "Bobby"
        assert profile["llm_model"] == "codellama"

    def test_update_empty_is_noop(self, tmp_db):
        repo = ProfileRepository(tmp_db)
        repo.create({"name": "Carol"})
        repo.update({})  # Should not raise
        assert repo.get()["name"] == "Carol"

    def test_get_returns_none_when_empty(self, tmp_db):
        repo = ProfileRepository(tmp_db)
        assert repo.get() is None

    def test_exists_false_when_empty(self, tmp_db):
        repo = ProfileRepository(tmp_db)
        assert not repo.exists()

    def test_create_idempotent_via_replace(self, tmp_db):
        repo = ProfileRepository(tmp_db)
        repo.create({"name": "Dan"})
        repo.create({"name": "Dave"})  # INSERT OR REPLACE
        assert repo.get()["name"] == "Dave"
