-- Migration 003: Chat history

CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL DEFAULT 'default',
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    context_json    TEXT DEFAULT '{}',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_conversation ON chat_messages(conversation_id, created_at);
