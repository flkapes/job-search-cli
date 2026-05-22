-- Migration 009: Interview simulation metadata support

ALTER TABLE practice_sessions ADD COLUMN metadata_json TEXT DEFAULT '{}';
