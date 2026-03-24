-- Migration 001: Initial schema

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS user_profile (
    id                  INTEGER PRIMARY KEY,
    name                TEXT,
    resume_text         TEXT,
    resume_parsed_json  TEXT,
    target_role         TEXT,
    experience_level    TEXT DEFAULT 'mid',
    llm_backend         TEXT DEFAULT 'ollama',
    llm_model           TEXT DEFAULT 'llama3',
    llm_base_url        TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS problems (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT DEFAULT 'static',
    category        TEXT NOT NULL,
    subcategory     TEXT,
    difficulty      TEXT DEFAULT 'medium',
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    constraints     TEXT,
    examples_json   TEXT DEFAULT '[]',
    hints_json      TEXT DEFAULT '[]',
    solution_json   TEXT,
    tags_json       TEXT DEFAULT '[]',
    times_shown     INTEGER DEFAULT 0,
    times_solved    INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS practice_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type    TEXT DEFAULT 'free',
    plan_id         INTEGER,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at        DATETIME,
    total_problems  INTEGER DEFAULT 0,
    solved_count    INTEGER DEFAULT 0,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS problem_attempts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER REFERENCES practice_sessions(id) ON DELETE CASCADE,
    problem_id          INTEGER REFERENCES problems(id),
    user_code           TEXT,
    user_explanation    TEXT,
    ai_feedback         TEXT,
    ai_score            REAL DEFAULT 0.0,
    time_spent_sec      INTEGER DEFAULT 0,
    hints_used          INTEGER DEFAULT 0,
    passed              INTEGER DEFAULT 0,
    attempted_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attempts_session ON problem_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_attempts_problem ON problem_attempts(problem_id);
CREATE INDEX IF NOT EXISTS idx_problems_category ON problems(category, subcategory);
CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON problems(difficulty);
