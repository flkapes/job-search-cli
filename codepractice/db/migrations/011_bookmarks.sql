-- Migration 011: Problem bookmarking for the solution library

ALTER TABLE problems ADD COLUMN bookmarked_at DATETIME;

CREATE INDEX IF NOT EXISTS idx_problems_bookmarked ON problems(bookmarked_at);
