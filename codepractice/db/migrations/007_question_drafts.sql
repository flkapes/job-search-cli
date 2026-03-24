-- Migration 007: Freeform interview question drafts

CREATE TABLE IF NOT EXISTS question_drafts (
    question_hash  TEXT PRIMARY KEY,
    source_type    TEXT NOT NULL,
    draft_text     TEXT NOT NULL DEFAULT '',
    updated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_question_drafts_source ON question_drafts(source_type);
