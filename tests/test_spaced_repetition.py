"""Tests for the SM-2 spaced repetition algorithm."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from codepractice.core.spaced_repetition import (
    _compute_next_interval,
    get_due_problems,
    get_review_stats,
    update_schedule,
)
from codepractice.db.repositories.problems import ProblemRepository


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_problem(db, title: str = "Test Problem") -> int:
    repo = ProblemRepository(db)
    return repo.create({
        "source": "static",
        "category": "dsa",
        "subcategory": "arrays",
        "difficulty": "easy",
        "title": title,
        "description": "Solve this.",
    })


# ── _compute_next_interval (pure function) ─────────────────────────────────────

class TestComputeNextInterval:
    def test_first_correct_answer(self):
        reps, interval, ease = _compute_next_interval(0, 1, 2.5, score=0.8)
        assert reps == 1
        assert interval == 1
        assert ease > 2.5  # rewarded

    def test_second_correct_answer(self):
        reps, interval, ease = _compute_next_interval(1, 1, 2.5, score=0.8)
        assert reps == 2
        assert interval == 6

    def test_third_correct_grows_by_ease(self):
        reps, interval, ease = _compute_next_interval(2, 6, 2.5, score=0.8)
        assert reps == 3
        assert interval == round(6 * 2.5)
        assert ease >= 1.3

    def test_incorrect_resets_to_one(self):
        reps, interval, ease = _compute_next_interval(5, 30, 2.5, score=0.3)
        assert reps == 0
        assert interval == 1
        assert ease < 2.5  # penalised

    def test_incorrect_boundary_score_059(self):
        """Score of 0.59 should be treated as incorrect."""
        reps, interval, ease = _compute_next_interval(3, 10, 2.5, score=0.59)
        assert reps == 0
        assert interval == 1

    def test_correct_boundary_score_060(self):
        """Score of 0.60 should be treated as correct."""
        reps, interval, ease = _compute_next_interval(0, 1, 2.5, score=0.60)
        assert reps == 1

    def test_ease_floor_at_1_3(self):
        """Ease factor should never drop below 1.3."""
        _, _, ease = _compute_next_interval(0, 1, 1.3, score=0.0)
        assert ease >= 1.3

    def test_perfect_score_increases_ease(self):
        _, _, ease = _compute_next_interval(2, 6, 2.5, score=1.0)
        assert ease > 2.5

    def test_low_but_passing_score_increases_ease_less_than_perfect(self):
        """A borderline pass increases ease less than a perfect score."""
        _, _, ease_borderline = _compute_next_interval(2, 6, 2.5, score=0.6)
        _, _, ease_perfect = _compute_next_interval(2, 6, 2.5, score=1.0)
        assert ease_borderline < ease_perfect
        assert ease_borderline >= 1.3  # floor holds


# ── update_schedule (DB integration) ──────────────────────────────────────────

class TestUpdateSchedule:
    def test_creates_schedule_row(self, tmp_db):
        pid = _make_problem(tmp_db)
        update_schedule(tmp_db, pid, score=0.8)

        with tmp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM review_schedule WHERE problem_id = ?", (pid,)
            ).fetchone()
        assert row is not None
        assert row["repetitions"] == 1
        assert row["last_score"] == pytest.approx(0.8)

    def test_updates_existing_schedule(self, tmp_db):
        pid = _make_problem(tmp_db)
        update_schedule(tmp_db, pid, score=0.8)
        update_schedule(tmp_db, pid, score=0.9)

        with tmp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM review_schedule WHERE problem_id = ?", (pid,)
            ).fetchone()
        assert row["repetitions"] == 2
        assert row["last_score"] == pytest.approx(0.9)

    def test_incorrect_answer_resets_repetitions(self, tmp_db):
        pid = _make_problem(tmp_db)
        update_schedule(tmp_db, pid, score=0.9)  # rep=1
        update_schedule(tmp_db, pid, score=0.9)  # rep=2
        update_schedule(tmp_db, pid, score=0.2)  # wrong → rep=0

        with tmp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM review_schedule WHERE problem_id = ?", (pid,)
            ).fetchone()
        assert row["repetitions"] == 0
        assert row["interval_days"] == 1

    def test_next_review_date_set(self, tmp_db):
        pid = _make_problem(tmp_db)
        update_schedule(tmp_db, pid, score=0.8)

        with tmp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT next_review FROM review_schedule WHERE problem_id = ?", (pid,)
            ).fetchone()

        next_date = date.fromisoformat(row["next_review"])
        assert next_date >= date.today()

    def test_wrong_answer_scheduled_tomorrow(self, tmp_db):
        pid = _make_problem(tmp_db)
        update_schedule(tmp_db, pid, score=0.1)  # incorrect

        with tmp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT next_review FROM review_schedule WHERE problem_id = ?", (pid,)
            ).fetchone()

        next_date = date.fromisoformat(row["next_review"])
        assert next_date == date.today() + timedelta(days=1)


# ── get_due_problems ───────────────────────────────────────────────────────────

class TestGetDueProblems:
    def _insert_review(self, db, problem_id: int, next_review: str):
        """Directly insert a review_schedule row for testing."""
        from datetime import datetime
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO review_schedule
                    (problem_id, next_review, interval_days, ease_factor, repetitions, last_score, updated_at)
                VALUES (?, ?, 1, 2.5, 1, 0.8, ?)
                """,
                (problem_id, next_review, datetime.now().isoformat()),
            )

    def test_returns_due_problems(self, tmp_db):
        pid1 = _make_problem(tmp_db, "P1")
        pid2 = _make_problem(tmp_db, "P2")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self._insert_review(tmp_db, pid1, yesterday)
        self._insert_review(tmp_db, pid2, yesterday)

        due = get_due_problems(tmp_db, n=10)
        assert pid1 in due
        assert pid2 in due

    def test_excludes_future_reviews(self, tmp_db):
        pid = _make_problem(tmp_db)
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self._insert_review(tmp_db, pid, tomorrow)

        due = get_due_problems(tmp_db, n=10)
        assert pid not in due

    def test_respects_limit(self, tmp_db):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        for i in range(5):
            pid = _make_problem(tmp_db, f"P{i}")
            self._insert_review(tmp_db, pid, yesterday)

        due = get_due_problems(tmp_db, n=3)
        assert len(due) == 3

    def test_empty_when_no_schedule(self, tmp_db):
        due = get_due_problems(tmp_db)
        assert due == []


# ── get_review_stats ───────────────────────────────────────────────────────────

class TestGetReviewStats:
    def _insert_review(self, db, problem_id: int, next_review: str):
        from datetime import datetime
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO review_schedule
                    (problem_id, next_review, interval_days, ease_factor, repetitions, last_score, updated_at)
                VALUES (?, ?, 1, 2.5, 1, 0.8, ?)
                """,
                (problem_id, next_review, datetime.now().isoformat()),
            )

    def test_stats_empty_db(self, tmp_db):
        stats = get_review_stats(tmp_db)
        assert stats["due_today"] == 0
        assert stats["due_this_week"] == 0
        assert stats["total_tracked"] == 0

    def test_stats_counts_due_today(self, tmp_db):
        today = date.today().isoformat()
        pid1 = _make_problem(tmp_db, "A")
        pid2 = _make_problem(tmp_db, "B")
        self._insert_review(tmp_db, pid1, today)
        self._insert_review(tmp_db, pid2, today)

        stats = get_review_stats(tmp_db)
        assert stats["due_today"] == 2

    def test_stats_future_not_in_today(self, tmp_db):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        pid = _make_problem(tmp_db)
        self._insert_review(tmp_db, pid, tomorrow)

        stats = get_review_stats(tmp_db)
        assert stats["due_today"] == 0
        assert stats["due_this_week"] >= 1  # tomorrow is within 7 days

    def test_total_tracked_counts_all(self, tmp_db):
        today = date.today().isoformat()
        future = (date.today() + timedelta(days=3)).isoformat()
        pid1 = _make_problem(tmp_db, "X")
        pid2 = _make_problem(tmp_db, "Y")
        self._insert_review(tmp_db, pid1, today)
        self._insert_review(tmp_db, pid2, future)

        stats = get_review_stats(tmp_db)
        assert stats["total_tracked"] == 2
