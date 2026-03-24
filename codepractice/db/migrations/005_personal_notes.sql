-- Migration 005: Personal notes on problems and weak-area drill session type

ALTER TABLE problems ADD COLUMN user_notes TEXT NOT NULL DEFAULT '';
