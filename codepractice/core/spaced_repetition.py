"""Spaced repetition scheduling using the SM-2 algorithm.

SM-2 (SuperMemo 2) schedules problem reviews based on recall quality:
- Correct answers grow the review interval exponentially
- Incorrect answers reset to re-review the next day
- Ease factor adjusts per problem based on performance history
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from codepractice.db.database import DatabaseManager

# ── Core SM-2 Algorithm ────────────────────────────────────────────────────────


def _compute_next_interval(
    repetitions: int,
    interval_days: int,
    ease_factor: float,
    score: float,
) -> tuple[int, int, float]:
    """Return (new_repetitions, new_interval_days, new_ease_factor)."""
    if score < 0.6:
        # Incorrect — reset to beginning
        return 0, 1, max(1.3, ease_factor - 0.2)

    # Correct — advance schedule
    new_reps = repetitions + 1
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = round(interval_days * ease_factor)

    # Adjust ease factor: reward high scores, penalise borderline ones
    new_ease = ease_factor + 0.1 - (1.0 - score) * (0.08 + (1.0 - score) * 0.02)
    new_ease = max(1.3, round(new_ease, 4))

    return new_reps, new_interval, new_ease


# ── DB Helpers ─────────────────────────────────────────────────────────────────


def update_schedule(db: DatabaseManager, problem_id: int, score: float) -> None:
    """Record a review result and compute the next review date."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT repetitions, interval_days, ease_factor FROM review_schedule WHERE problem_id = ?",
            (problem_id,),
        ).fetchone()

    if row:
        reps, interval, ease = row["repetitions"], row["interval_days"], row["ease_factor"]
    else:
        reps, interval, ease = 0, 1, 2.5

    new_reps, new_interval, new_ease = _compute_next_interval(reps, interval, ease, score)
    next_review = (date.today() + timedelta(days=new_interval)).isoformat()

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO review_schedule
                (problem_id, next_review, interval_days, ease_factor, repetitions, last_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(problem_id) DO UPDATE SET
                next_review   = excluded.next_review,
                interval_days = excluded.interval_days,
                ease_factor   = excluded.ease_factor,
                repetitions   = excluded.repetitions,
                last_score    = excluded.last_score,
                updated_at    = excluded.updated_at
            """,
            (problem_id, next_review, new_interval, new_ease, new_reps, score, datetime.now().isoformat()),
        )


def get_due_problems(db: DatabaseManager, n: int = 10) -> list[int]:
    """Return up to *n* problem IDs whose next review date is today or earlier."""
    today = date.today().isoformat()
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT rs.problem_id
            FROM review_schedule rs
            JOIN problems p ON rs.problem_id = p.id
            WHERE rs.next_review <= ?
            ORDER BY rs.next_review ASC, rs.ease_factor ASC
            LIMIT ?
            """,
            (today, n),
        ).fetchall()
    return [r["problem_id"] for r in rows]


def get_review_stats(db: DatabaseManager) -> dict:
    """Return summary stats: due today, due this week, total tracked."""
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()

    with db.get_connection() as conn:
        due_today = conn.execute(
            "SELECT COUNT(*) as cnt FROM review_schedule WHERE next_review <= ?",
            (today,),
        ).fetchone()["cnt"]

        due_week = conn.execute(
            "SELECT COUNT(*) as cnt FROM review_schedule WHERE next_review <= ?",
            (week_end,),
        ).fetchone()["cnt"]

        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM review_schedule",
        ).fetchone()["cnt"]

    return {
        "due_today": due_today,
        "due_this_week": due_week,
        "total_tracked": total,
    }
