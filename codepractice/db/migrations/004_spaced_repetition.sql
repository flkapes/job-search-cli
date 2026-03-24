-- Migration 004: Spaced repetition review schedule

CREATE TABLE IF NOT EXISTS review_schedule (
    problem_id    INTEGER PRIMARY KEY REFERENCES problems(id) ON DELETE CASCADE,
    next_review   TEXT    NOT NULL,          -- ISO-8601 date (YYYY-MM-DD)
    interval_days INTEGER NOT NULL DEFAULT 1,
    ease_factor   REAL    NOT NULL DEFAULT 2.5,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    last_score    REAL,
    updated_at    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_review_next ON review_schedule(next_review);
