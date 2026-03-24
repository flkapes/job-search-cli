-- Migration 002: Learning plans and progress tracking

CREATE TABLE IF NOT EXISTS learning_plans (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    title                   TEXT NOT NULL,
    natural_language_goal   TEXT,
    duration_days           INTEGER,
    current_day             INTEGER DEFAULT 1,
    status                  TEXT DEFAULT 'active',
    plan_json               TEXT DEFAULT '{}',
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plan_days (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id             INTEGER REFERENCES learning_plans(id) ON DELETE CASCADE,
    day_number          INTEGER NOT NULL,
    theme               TEXT,
    objectives_json     TEXT DEFAULT '[]',
    problem_ids_json    TEXT DEFAULT '[]',
    estimated_minutes   INTEGER DEFAULT 45,
    completed           INTEGER DEFAULT 0,
    completed_at        DATETIME,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS job_descriptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name        TEXT,
    role_title          TEXT,
    jd_text             TEXT NOT NULL,
    parsed_skills_json  TEXT DEFAULT '[]',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date       DATE DEFAULT CURRENT_DATE,
    problems_solved     INTEGER DEFAULT 0,
    avg_score           REAL DEFAULT 0.0,
    streak_days         INTEGER DEFAULT 0,
    weak_areas_json     TEXT DEFAULT '[]',
    strong_areas_json   TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_plan_days_plan ON plan_days(plan_id, day_number);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON progress_snapshots(snapshot_date);
