"""Custom problem creation: validation, persistence, and JSON export/import."""

from __future__ import annotations

import json
from pathlib import Path

from codepractice.core.models import Example, Problem, ProblemSource, Solution


def build_custom_problem(
    title: str,
    description: str,
    category: str = "practical",
    subcategory: str = "",
    difficulty: str = "medium",
    examples: list[dict] | None = None,
    hints: list[str] | None = None,
    solution_code: str = "",
    solution_explanation: str = "",
    tags: list[str] | None = None,
) -> Problem:
    """Validate form fields and construct a custom Problem. Raises ValueError."""
    title = title.strip()
    description = description.strip()
    if not title:
        raise ValueError("Title is required")
    if not description:
        raise ValueError("Description is required")
    if difficulty not in ("easy", "medium", "hard"):
        raise ValueError(f"Invalid difficulty: {difficulty}")

    parsed_examples = [
        Example(input=str(e.get("input", "")).strip(), output=str(e.get("output", "")).strip(),
                explanation=str(e.get("explanation", "")).strip())
        for e in (examples or [])
        if str(e.get("input", "")).strip() or str(e.get("output", "")).strip()
    ]

    solution = None
    if solution_code.strip():
        solution = Solution(code=solution_code.strip(), explanation=solution_explanation.strip())

    return Problem(
        source=ProblemSource.custom,
        category=category,
        subcategory=subcategory.strip(),
        difficulty=difficulty,
        title=title,
        description=description,
        examples=parsed_examples,
        hints=[h.strip() for h in (hints or []) if h.strip()],
        solution=solution,
        tags=[t.strip() for t in (tags or []) if t.strip()],
    )


def export_custom_problems(problem_repo, path: Path) -> int:
    """Write all source='custom' problems to a shareable JSON file."""
    rows = problem_repo.get_by_source("custom")
    problems = []
    for row in rows:
        problems.append({
            "source": "custom",
            "category": row.get("category", "practical"),
            "subcategory": row.get("subcategory", ""),
            "difficulty": row.get("difficulty", "medium"),
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "constraints": row.get("constraints", ""),
            "examples": row.get("examples", []),
            "hints": row.get("hints", []),
            "solution": row.get("solution"),
            "tags": row.get("tags", []),
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"problems": problems}, indent=2))
    return len(problems)


def import_custom_problems(problem_repo, path: Path) -> int:
    """Load problems from a JSON export and insert them as source='custom'.

    Skips entries that fail validation and duplicates (same title already
    stored as a custom problem).
    """
    data = json.loads(path.read_text())
    entries = data.get("problems", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("Invalid file: expected a list of problems")

    existing_titles = {p.get("title", "") for p in problem_repo.get_by_source("custom")}
    imported = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            problem = build_custom_problem(
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                category=entry.get("category", "practical"),
                subcategory=entry.get("subcategory", ""),
                difficulty=entry.get("difficulty", "medium"),
                examples=entry.get("examples", []),
                hints=entry.get("hints", []),
                solution_code=(entry.get("solution") or {}).get("code", ""),
                solution_explanation=(entry.get("solution") or {}).get("explanation", ""),
                tags=entry.get("tags", []),
            )
        except ValueError:
            continue
        if problem.title in existing_titles:
            continue
        problem_repo.create(problem.to_db())
        existing_titles.add(problem.title)
        imported += 1
    return imported
