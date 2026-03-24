"""Tests for weak-area auto-drill — Feature 4."""

from __future__ import annotations

from codepractice.core.difficulty import should_show_weak_area_drill
from codepractice.db.repositories import ProblemRepository, SessionRepository


class TestShouldShowWeakAreaDrill:
    def test_shows_when_weak_area_exists(self):
        scores = [
            {"category": "dsa", "subcategory": "dp", "avg_score": 0.3, "attempts": 3},
        ]
        assert should_show_weak_area_drill(scores) is True

    def test_hides_when_no_weak_areas(self):
        scores = [
            {"category": "dsa", "subcategory": "dp", "avg_score": 0.9, "attempts": 3},
            {"category": "dsa", "subcategory": "bfs", "avg_score": 0.85, "attempts": 4},
        ]
        assert should_show_weak_area_drill(scores) is False

    def test_hides_when_insufficient_attempts(self):
        scores = [
            {"category": "dsa", "subcategory": "dp", "avg_score": 0.1, "attempts": 1},
        ]
        assert should_show_weak_area_drill(scores) is False

    def test_hides_on_empty_scores(self):
        assert should_show_weak_area_drill([]) is False

    def test_threshold_is_below_06(self):
        """Areas with avg_score < 0.6 are weak."""
        at_boundary = [{"category": "dsa", "subcategory": "dp", "avg_score": 0.59, "attempts": 3}]
        above_boundary = [{"category": "dsa", "subcategory": "dp", "avg_score": 0.60, "attempts": 3}]
        assert should_show_weak_area_drill(at_boundary) is True
        assert should_show_weak_area_drill(above_boundary) is False

    def test_shows_when_mixed_areas(self):
        scores = [
            {"category": "dsa", "subcategory": "dp", "avg_score": 0.2, "attempts": 5},
            {"category": "dsa", "subcategory": "bfs", "avg_score": 0.95, "attempts": 5},
        ]
        assert should_show_weak_area_drill(scores) is True


class TestWeakAreaDrillSessionType:
    def test_weak_area_drill_session_type_stored(self, tmp_db):
        sess_repo = SessionRepository(tmp_db)
        sid = sess_repo.start_session(session_type="weak_area_drill")
        session = sess_repo.get_session(sid)
        assert session["session_type"] == "weak_area_drill"

    def test_get_sessions_by_type_returns_matching(self, tmp_db):
        sess_repo = SessionRepository(tmp_db)
        sess_repo.start_session(session_type="free")
        sess_repo.start_session(session_type="weak_area_drill")
        sess_repo.start_session(session_type="weak_area_drill")

        drills = sess_repo.get_sessions_by_type("weak_area_drill")
        assert len(drills) == 2
        assert all(s["session_type"] == "weak_area_drill" for s in drills)

    def test_get_sessions_by_type_empty_when_none(self, tmp_db):
        sess_repo = SessionRepository(tmp_db)
        sess_repo.start_session(session_type="free")
        assert sess_repo.get_sessions_by_type("weak_area_drill") == []

    def test_drill_attempts_tracked_separately(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "subcategory": "dp", "title": "T", "description": "D"})

        free_sid = sess_repo.start_session(session_type="free")
        sess_repo.record_attempt({"session_id": free_sid, "problem_id": pid, "user_code": "", "ai_feedback": "", "ai_score": 0.5})

        drill_sid = sess_repo.start_session(session_type="weak_area_drill")
        sess_repo.record_attempt({"session_id": drill_sid, "problem_id": pid, "user_code": "", "ai_feedback": "", "ai_score": 0.7})

        drills = sess_repo.get_sessions_by_type("weak_area_drill")
        assert len(drills) == 1
