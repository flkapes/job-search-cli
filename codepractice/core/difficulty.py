"""Adaptive difficulty engine — promotes/demotes difficulty based on attempt history."""

from __future__ import annotations

from codepractice.config import (
    ADAPTIVE_WINDOW,
    DIFFICULTY_DEMOTION_THRESHOLD,
    DIFFICULTY_PROMOTION_THRESHOLD,
    SCORE_WEIGHTS,
)
from codepractice.core.models import Difficulty


def compute_composite_score(
    correctness: float,
    efficiency: float,
    style: float,
) -> float:
    """Weighted composite score from three subscores."""
    return (
        correctness * SCORE_WEIGHTS["correctness"]
        + efficiency * SCORE_WEIGHTS["efficiency"]
        + style * SCORE_WEIGHTS["style"]
    )


def suggest_next_difficulty(
    attempts: list[dict],
    current_difficulty: str = "medium",
) -> str:
    """
    Given recent attempt dicts (with ai_score field), suggest next difficulty.
    Each dict should have: {'ai_score': float, 'passed': bool}
    """
    if not attempts:
        return current_difficulty

    recent = attempts[-ADAPTIVE_WINDOW:]
    avg_score = sum(a.get("ai_score", 0.0) for a in recent) / len(recent)

    difficulty_order = [Difficulty.easy, Difficulty.medium, Difficulty.hard]
    try:
        current_idx = difficulty_order.index(Difficulty(current_difficulty))
    except ValueError:
        current_idx = 1  # default to medium

    if avg_score >= DIFFICULTY_PROMOTION_THRESHOLD and current_idx < len(difficulty_order) - 1:
        return difficulty_order[current_idx + 1].value
    if avg_score <= DIFFICULTY_DEMOTION_THRESHOLD and current_idx > 0:
        return difficulty_order[current_idx - 1].value
    return current_difficulty


def get_weak_areas(category_scores: list[dict]) -> list[str]:
    """Return categories/subcategories with lowest average scores."""
    scored = [
        (f"{r.get('category', '')}/{r.get('subcategory', '')}", r.get("avg_score", 0.0))
        for r in category_scores
        if r.get("attempts", 0) >= 2
    ]
    scored.sort(key=lambda x: x[1])
    return [area for area, _ in scored[:3]]


def get_strong_areas(category_scores: list[dict]) -> list[str]:
    """Return categories/subcategories with highest average scores."""
    scored = [
        (f"{r.get('category', '')}/{r.get('subcategory', '')}", r.get("avg_score", 0.0))
        for r in category_scores
        if r.get("attempts", 0) >= 2
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [area for area, _ in scored[:3]]
