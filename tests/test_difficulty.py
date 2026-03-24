"""Tests for the adaptive difficulty engine."""

from __future__ import annotations

import pytest

from codepractice.core.difficulty import (
    compute_composite_score,
    get_strong_areas,
    get_weak_areas,
    suggest_next_difficulty,
)
from codepractice.config import (
    ADAPTIVE_WINDOW,
    DIFFICULTY_DEMOTION_THRESHOLD,
    DIFFICULTY_PROMOTION_THRESHOLD,
    SCORE_WEIGHTS,
)


# ── compute_composite_score ────────────────────────────────────────────────────

class TestCompositeScore:
    def test_perfect_scores(self):
        score = compute_composite_score(1.0, 1.0, 1.0)
        assert score == pytest.approx(1.0)

    def test_zero_scores(self):
        score = compute_composite_score(0.0, 0.0, 0.0)
        assert score == pytest.approx(0.0)

    def test_weighted_correctness(self):
        # Only correctness is 1.0
        score = compute_composite_score(1.0, 0.0, 0.0)
        assert score == pytest.approx(SCORE_WEIGHTS["correctness"])

    def test_weighted_efficiency(self):
        score = compute_composite_score(0.0, 1.0, 0.0)
        assert score == pytest.approx(SCORE_WEIGHTS["efficiency"])

    def test_weighted_style(self):
        score = compute_composite_score(0.0, 0.0, 1.0)
        assert score == pytest.approx(SCORE_WEIGHTS["style"])

    def test_weights_sum_to_one(self):
        total = SCORE_WEIGHTS["correctness"] + SCORE_WEIGHTS["efficiency"] + SCORE_WEIGHTS["style"]
        assert total == pytest.approx(1.0)

    def test_typical_score(self):
        score = compute_composite_score(0.8, 0.6, 0.9)
        expected = 0.8 * SCORE_WEIGHTS["correctness"] + 0.6 * SCORE_WEIGHTS["efficiency"] + 0.9 * SCORE_WEIGHTS["style"]
        assert score == pytest.approx(expected)


# ── suggest_next_difficulty ────────────────────────────────────────────────────

class TestSuggestNextDifficulty:
    def _make_attempts(self, score: float, n: int = ADAPTIVE_WINDOW) -> list[dict]:
        return [{"ai_score": score, "passed": score >= 0.7} for _ in range(n)]

    def test_empty_attempts_returns_current(self):
        assert suggest_next_difficulty([], "medium") == "medium"

    def test_high_scores_promote_from_easy(self):
        attempts = self._make_attempts(DIFFICULTY_PROMOTION_THRESHOLD + 0.01)
        result = suggest_next_difficulty(attempts, "easy")
        assert result == "medium"

    def test_high_scores_promote_from_medium(self):
        attempts = self._make_attempts(DIFFICULTY_PROMOTION_THRESHOLD + 0.01)
        result = suggest_next_difficulty(attempts, "medium")
        assert result == "hard"

    def test_high_scores_no_promote_from_hard(self):
        """Cannot go above hard."""
        attempts = self._make_attempts(1.0)
        result = suggest_next_difficulty(attempts, "hard")
        assert result == "hard"

    def test_low_scores_demote_from_hard(self):
        attempts = self._make_attempts(DIFFICULTY_DEMOTION_THRESHOLD - 0.01)
        result = suggest_next_difficulty(attempts, "hard")
        assert result == "medium"

    def test_low_scores_demote_from_medium(self):
        attempts = self._make_attempts(DIFFICULTY_DEMOTION_THRESHOLD - 0.01)
        result = suggest_next_difficulty(attempts, "medium")
        assert result == "easy"

    def test_low_scores_no_demote_from_easy(self):
        """Cannot go below easy."""
        attempts = self._make_attempts(0.0)
        result = suggest_next_difficulty(attempts, "easy")
        assert result == "easy"

    def test_middle_scores_stay_same(self):
        mid_score = (DIFFICULTY_PROMOTION_THRESHOLD + DIFFICULTY_DEMOTION_THRESHOLD) / 2
        attempts = self._make_attempts(mid_score)
        result = suggest_next_difficulty(attempts, "medium")
        assert result == "medium"

    def test_only_recent_window_considered(self):
        """Old bad attempts should not affect decision if recent are good."""
        old_bad = self._make_attempts(0.0, n=10)
        recent_good = self._make_attempts(DIFFICULTY_PROMOTION_THRESHOLD + 0.1, n=ADAPTIVE_WINDOW)
        result = suggest_next_difficulty(old_bad + recent_good, "easy")
        assert result == "medium"

    def test_invalid_difficulty_defaults_to_medium(self):
        attempts = self._make_attempts(1.0)
        result = suggest_next_difficulty(attempts, "unknown")
        assert result == "hard"  # defaulted to medium index=1, then promoted

    def test_exact_promotion_threshold(self):
        attempts = self._make_attempts(DIFFICULTY_PROMOTION_THRESHOLD)
        result = suggest_next_difficulty(attempts, "easy")
        assert result == "medium"

    def test_exact_demotion_threshold(self):
        # The code uses <=, so exactly at the demotion threshold triggers demotion
        attempts = self._make_attempts(DIFFICULTY_DEMOTION_THRESHOLD)
        result = suggest_next_difficulty(attempts, "hard")
        assert result == "medium"


# ── weak/strong area identification ───────────────────────────────────────────

class TestAreaIdentification:
    def _make_category_scores(self):
        return [
            {"category": "dsa", "subcategory": "two_pointers", "avg_score": 0.9, "attempts": 5},
            {"category": "dsa", "subcategory": "dynamic_programming", "avg_score": 0.3, "attempts": 4},
            {"category": "dsa", "subcategory": "bfs", "avg_score": 0.5, "attempts": 3},
            {"category": "python", "subcategory": "threading", "avg_score": 0.2, "attempts": 2},
            {"category": "python", "subcategory": "oop", "avg_score": 0.85, "attempts": 6},
        ]

    def test_weak_areas_sorted_ascending(self):
        scores = self._make_category_scores()
        weak = get_weak_areas(scores)
        assert len(weak) <= 3
        # threading (0.2) and dynamic_programming (0.3) should appear
        assert any("threading" in w for w in weak)
        assert any("dynamic_programming" in w for w in weak)

    def test_strong_areas_sorted_descending(self):
        scores = self._make_category_scores()
        strong = get_strong_areas(scores)
        assert len(strong) <= 3
        assert any("two_pointers" in s for s in strong)

    def test_minimum_attempts_filter(self):
        """Categories with < 2 attempts should be excluded."""
        scores = [
            {"category": "dsa", "subcategory": "new_topic", "avg_score": 0.0, "attempts": 1},
            {"category": "dsa", "subcategory": "old_topic", "avg_score": 0.9, "attempts": 5},
        ]
        weak = get_weak_areas(scores)
        # new_topic has only 1 attempt, should be excluded
        assert not any("new_topic" in w for w in weak)

    def test_empty_scores(self):
        assert get_weak_areas([]) == []
        assert get_strong_areas([]) == []
