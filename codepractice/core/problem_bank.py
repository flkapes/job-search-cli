"""Static problem bank loader — seeds the DB with curated problems."""

from __future__ import annotations

import json

from codepractice.config import PROBLEMS_DATA_DIR


def load_all_problems() -> list[dict]:
    """Load all static problem JSON files."""
    problems: list[dict] = []
    if not PROBLEMS_DATA_DIR.exists():
        return problems

    for json_file in sorted(PROBLEMS_DATA_DIR.glob("*.json")):
        try:
            data = json.loads(json_file.read_text())
            if isinstance(data, list):
                problems.extend(data)
            elif isinstance(data, dict) and "problems" in data:
                problems.extend(data["problems"])
        except (json.JSONDecodeError, OSError):
            continue

    return problems


def get_problems_for_category(category: str, subcategory: str | None = None) -> list[dict]:
    all_problems = load_all_problems()
    result = [p for p in all_problems if p.get("category") == category]
    if subcategory:
        result = [p for p in result if p.get("subcategory") == subcategory]
    return result
