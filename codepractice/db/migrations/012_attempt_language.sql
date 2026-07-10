-- Migration 012: Track the programming language used per attempt

ALTER TABLE problem_attempts ADD COLUMN language TEXT DEFAULT 'python';
