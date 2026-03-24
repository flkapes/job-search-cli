"""Tests for session replay (get_attempt_by_id) — Feature 2."""

from __future__ import annotations

import pytest

from codepractice.db.repositories import ProblemRepository, SessionRepository


def _make_attempt(prob_repo, sess_repo, code="def solve(): pass", score=0.8):
    pid = prob_repo.create({"category": "dsa", "title": "Two Sum", "description": "Find pair"})
    sid = sess_repo.start_session()
    aid = sess_repo.record_attempt({
        "session_id": sid,
        "problem_id": pid,
        "user_code": code,
        "ai_feedback": "Great work!",
        "ai_score": score,
        "time_spent_sec": 90,
        "hints_used": 2,
        "passed": score >= 0.7,
    })
    return pid, sid, aid


class TestGetAttemptById:
    def test_returns_attempt_data(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)
        pid, sid, aid = _make_attempt(prob_repo, sess_repo)

        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt is not None
        assert attempt["user_code"] == "def solve(): pass"
        assert attempt["ai_feedback"] == "Great work!"
        assert attempt["ai_score"] == pytest.approx(0.8)
        assert attempt["hints_used"] == 2
        assert attempt["time_spent_sec"] == 90

    def test_includes_problem_title(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)
        _make_attempt(prob_repo, sess_repo)

        pid = prob_repo.create({"category": "dsa", "title": "Max Subarray", "description": "D"})
        sid = sess_repo.start_session()
        aid = sess_repo.record_attempt({
            "session_id": sid, "problem_id": pid,
            "user_code": "x=1", "ai_feedback": "", "ai_score": 0.5,
        })

        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt["problem_title"] == "Max Subarray"

    def test_nonexistent_returns_none(self, tmp_db):
        sess_repo = SessionRepository(tmp_db)
        assert sess_repo.get_attempt_by_id(99999) is None

    def test_returns_passed_field(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)
        _, _, aid = _make_attempt(prob_repo, sess_repo, score=0.9)

        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt["passed"] == 1

    def test_returns_failed_attempt(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)
        _, _, aid = _make_attempt(prob_repo, sess_repo, score=0.3)

        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt["passed"] == 0


class TestGetAttemptsForSession:
    def test_returns_all_attempts_in_session(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "title": "Q", "description": "D"})
        sid = sess_repo.start_session()
        sess_repo.record_attempt({"session_id": sid, "problem_id": pid, "user_code": "a", "ai_feedback": "", "ai_score": 0.5})
        sess_repo.record_attempt({"session_id": sid, "problem_id": pid, "user_code": "b", "ai_feedback": "", "ai_score": 0.9})

        attempts = sess_repo.get_attempts_for_session(sid)
        assert len(attempts) == 2

    def test_empty_session_returns_empty_list(self, tmp_db):
        sess_repo = SessionRepository(tmp_db)
        sid = sess_repo.start_session()
        attempts = sess_repo.get_attempts_for_session(sid)
        assert attempts == []

    def test_attempts_ordered_by_time(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "title": "Q", "description": "D"})
        sid = sess_repo.start_session()
        sess_repo.record_attempt({"session_id": sid, "problem_id": pid, "user_code": "first", "ai_feedback": "", "ai_score": 0.5})
        sess_repo.record_attempt({"session_id": sid, "problem_id": pid, "user_code": "second", "ai_feedback": "", "ai_score": 0.8})

        attempts = sess_repo.get_attempts_for_session(sid)
        codes = [a["user_code"] for a in attempts]
        assert codes.index("first") < codes.index("second")
