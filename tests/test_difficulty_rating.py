"""Tests for per-problem personal difficulty rating — Feature 8."""

from __future__ import annotations

import pytest

from codepractice.db.repositories import ProblemRepository, SessionRepository


def _setup(tmp_db, difficulty="medium"):
    prob_repo = ProblemRepository(tmp_db)
    sess_repo = SessionRepository(tmp_db)
    pid = prob_repo.create({
        "category": "dsa", "difficulty": difficulty,
        "title": "Test Problem", "description": "D",
    })
    sid = sess_repo.start_session()
    aid = sess_repo.record_attempt({
        "session_id": sid, "problem_id": pid,
        "user_code": "", "ai_feedback": "", "ai_score": 0.7,
    })
    return prob_repo, sess_repo, pid, aid


class TestSetDifficultyRating:
    def test_set_and_retrieve_rating(self, tmp_db):
        _, sess_repo, _, aid = _setup(tmp_db)
        sess_repo.set_difficulty_rating(aid, 4)
        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt["user_difficulty_rating"] == 4

    def test_default_rating_is_null(self, tmp_db):
        _, sess_repo, _, aid = _setup(tmp_db)
        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt["user_difficulty_rating"] is None

    def test_all_valid_ratings(self, tmp_db):
        _, sess_repo, _, _ = _setup(tmp_db)
        for rating in (1, 2, 3, 4, 5):
            pid2 = ProblemRepository(tmp_db).create({"category": "dsa", "title": f"P{rating}", "description": "D"})
            sid2 = sess_repo.start_session()
            aid2 = sess_repo.record_attempt({"session_id": sid2, "problem_id": pid2, "user_code": "", "ai_feedback": "", "ai_score": 0.5})
            sess_repo.set_difficulty_rating(aid2, rating)
            attempt = sess_repo.get_attempt_by_id(aid2)
            assert attempt["user_difficulty_rating"] == rating

    def test_rating_below_1_raises(self, tmp_db):
        _, sess_repo, _, aid = _setup(tmp_db)
        with pytest.raises(ValueError):
            sess_repo.set_difficulty_rating(aid, 0)

    def test_rating_above_5_raises(self, tmp_db):
        _, sess_repo, _, aid = _setup(tmp_db)
        with pytest.raises(ValueError):
            sess_repo.set_difficulty_rating(aid, 6)

    def test_update_existing_rating(self, tmp_db):
        _, sess_repo, _, aid = _setup(tmp_db)
        sess_repo.set_difficulty_rating(aid, 2)
        sess_repo.set_difficulty_rating(aid, 5)
        attempt = sess_repo.get_attempt_by_id(aid)
        assert attempt["user_difficulty_rating"] == 5


class TestGetMislabeledProblems:
    def _add_ratings(self, sess_repo, prob_repo, pid, scores_ratings, difficulty="medium"):
        """Add multiple attempts with ratings for a problem."""
        sid = sess_repo.start_session()
        for score, rating in scores_ratings:
            aid = sess_repo.record_attempt({
                "session_id": sid, "problem_id": pid,
                "user_code": "", "ai_feedback": "", "ai_score": score,
            })
            sess_repo.set_difficulty_rating(aid, rating)

    def test_easy_problem_rated_hard_is_mislabeled(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "difficulty": "easy", "title": "Sneaky", "description": "D"})
        # easy=1, user rates 5 — divergence of 4
        self._add_ratings(sess_repo, prob_repo, pid, [(0.5, 5), (0.6, 5), (0.4, 5)])

        mislabeled = sess_repo.get_mislabeled_problems()
        assert any(r["title"] == "Sneaky" for r in mislabeled)

    def test_correctly_labeled_not_mislabeled(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "difficulty": "medium", "title": "Fair", "description": "D"})
        # medium=3, user rates 3 — no divergence
        self._add_ratings(sess_repo, prob_repo, pid, [(0.7, 3), (0.8, 3), (0.6, 3)])

        mislabeled = sess_repo.get_mislabeled_problems()
        assert not any(r["title"] == "Fair" for r in mislabeled)

    def test_requires_minimum_ratings_to_appear(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "difficulty": "easy", "title": "Sparse", "description": "D"})
        # Only 1 rating — should be excluded (need >= 3)
        self._add_ratings(sess_repo, prob_repo, pid, [(0.5, 5)])

        mislabeled = sess_repo.get_mislabeled_problems()
        assert not any(r["title"] == "Sparse" for r in mislabeled)

    def test_empty_returns_empty_list(self, tmp_db):
        sess_repo = SessionRepository(tmp_db)
        assert sess_repo.get_mislabeled_problems() == []

    def test_mislabeled_result_includes_avg_rating(self, tmp_db):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "difficulty": "easy", "title": "Hard Easy", "description": "D"})
        self._add_ratings(sess_repo, prob_repo, pid, [(0.5, 5), (0.4, 5), (0.3, 5)])

        mislabeled = sess_repo.get_mislabeled_problems()
        row = next(r for r in mislabeled if r["title"] == "Hard Easy")
        assert "avg_user_rating" in row or "avg_rating" in row
