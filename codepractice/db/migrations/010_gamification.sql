-- Migration 010: Gamification — XP events and achievement unlocks

CREATE TABLE IF NOT EXISTS xp_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id      INTEGER REFERENCES problem_attempts(id) ON DELETE SET NULL,
    problem_id      INTEGER REFERENCES problems(id) ON DELETE SET NULL,
    xp              INTEGER NOT NULL,
    reason          TEXT DEFAULT '',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key             TEXT UNIQUE NOT NULL,
    unlocked_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_xp_events_created_at ON xp_events(created_at);
