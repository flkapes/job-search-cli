"""Repository for user profile."""

from __future__ import annotations

import json
from typing import Any

from codepractice.db.repositories.base import BaseRepository


class ProfileRepository(BaseRepository):

    def get(self) -> dict | None:
        row = self._execute_one("SELECT * FROM user_profile WHERE id = 1")
        if row is None:
            return None
        d = dict(row)
        try:
            d["resume_parsed"] = json.loads(d.get("resume_parsed_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["resume_parsed"] = {}
        return d

    def create(self, data: dict[str, Any]) -> None:
        self._insert(
            """INSERT OR REPLACE INTO user_profile
               (id, name, resume_text, resume_parsed_json, target_role,
                experience_level, llm_backend, llm_model, llm_base_url)
               VALUES (1,?,?,?,?,?,?,?,?)""",
            (
                data.get("name", ""),
                data.get("resume_text", ""),
                json.dumps(data.get("resume_parsed", {})),
                data.get("target_role", ""),
                data.get("experience_level", "mid"),
                data.get("llm_backend", "ollama"),
                data.get("llm_model", "llama3"),
                data.get("llm_base_url", ""),
            ),
        )

    def update(self, fields: dict[str, Any]) -> None:
        if not fields:
            return
        # Map field names to column names
        col_map = {
            "name": "name",
            "resume_text": "resume_text",
            "resume_parsed": "resume_parsed_json",
            "target_role": "target_role",
            "experience_level": "experience_level",
            "llm_backend": "llm_backend",
            "llm_model": "llm_model",
            "llm_base_url": "llm_base_url",
        }
        sets = []
        params = []
        for key, value in fields.items():
            col = col_map.get(key)
            if not col:
                continue
            sets.append(f"{col} = ?")
            if key == "resume_parsed":
                params.append(json.dumps(value))
            else:
                params.append(value)
        if not sets:
            return
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(1)
        self._update(f"UPDATE user_profile SET {', '.join(sets)} WHERE id = ?", tuple(params))

    def exists(self) -> bool:
        row = self._execute_one("SELECT id FROM user_profile WHERE id = 1")
        return row is not None
