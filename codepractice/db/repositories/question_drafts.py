"""Repository for freeform interview question drafts."""

from __future__ import annotations

from datetime import datetime

from codepractice.db.repositories.base import BaseRepository


class QuestionDraftsRepository(BaseRepository):
    """Stores user-authored draft answers to freeform interview questions."""

    def save_draft(self, question_hash: str, source_type: str, draft_text: str) -> None:
        """Upsert a draft answer keyed by question_hash."""
        now = datetime.utcnow().isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO question_drafts (question_hash, source_type, draft_text, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(question_hash) DO UPDATE SET
                       draft_text = excluded.draft_text,
                       source_type = excluded.source_type,
                       updated_at = excluded.updated_at""",
                (question_hash, source_type, draft_text, now),
            )

    def get_draft(self, question_hash: str) -> dict | None:
        """Return the draft for a question, or None if not found."""
        return self.row_to_dict(
            self._execute_one(
                "SELECT * FROM question_drafts WHERE question_hash = ?",
                (question_hash,),
            )
        )

    def list_drafts_for_source(self, source_type: str) -> list[dict]:
        """Return all drafts of a given source type (jd or resume)."""
        return self.rows_to_dicts(
            self._execute(
                "SELECT * FROM question_drafts WHERE source_type = ? ORDER BY updated_at DESC",
                (source_type,),
            )
        )

    def delete_draft(self, question_hash: str) -> None:
        """Remove a draft by question_hash."""
        self._update(
            "DELETE FROM question_drafts WHERE question_hash = ?",
            (question_hash,),
        )
