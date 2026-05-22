-- Migration 008: Goal history for adaptive plan evolution

CREATE TABLE IF NOT EXISTS goal_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER REFERENCES learning_plans(id) ON DELETE SET NULL,
    goal_text       TEXT NOT NULL,
    plan_summary    TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_goal_history_created_at ON goal_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_goal_history_plan_id ON goal_history(plan_id);
