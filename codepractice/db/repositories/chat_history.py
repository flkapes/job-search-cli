"""Repository for chat history."""

from __future__ import annotations

import json

from codepractice.db.repositories.base import BaseRepository


class ChatHistoryRepository(BaseRepository):

    def add_message(
        self,
        role: str,
        content: str,
        conversation_id: str = "default",
        context: dict | None = None,
    ) -> int:
        return self._insert(
            """INSERT INTO chat_messages (conversation_id, role, content, context_json)
               VALUES (?,?,?,?)""",
            (conversation_id, role, content, json.dumps(context or {})),
        )

    def get_history(self, conversation_id: str = "default", limit: int = 50) -> list[dict]:
        rows = self._execute(
            """SELECT * FROM chat_messages
               WHERE conversation_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (conversation_id, limit),
        )
        messages = [dict(r) for r in rows]
        messages.reverse()  # chronological order
        return messages

    def get_messages_for_llm(self, conversation_id: str = "default", limit: int = 20) -> list[dict]:
        """Return messages in LLM API format."""
        history = self.get_history(conversation_id, limit)
        return [{"role": m["role"], "content": m["content"]} for m in history]

    def clear_conversation(self, conversation_id: str = "default") -> None:
        self._update(
            "DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,)
        )

    def list_conversations(self) -> list[str]:
        rows = self._execute(
            "SELECT DISTINCT conversation_id FROM chat_messages ORDER BY MAX(created_at) DESC"
        )
        return [r["conversation_id"] for r in rows]
