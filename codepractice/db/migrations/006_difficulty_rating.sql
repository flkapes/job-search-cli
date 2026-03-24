-- Migration 006: Per-problem personal difficulty rating

ALTER TABLE problem_attempts ADD COLUMN user_difficulty_rating INTEGER;
