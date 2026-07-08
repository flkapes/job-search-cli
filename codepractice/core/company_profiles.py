"""Company interview profiles: loading, search, and targeted plan building."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from codepractice.config import COMPANIES_DATA_FILE, DSA_PATTERNS
from codepractice.core.models import DayPlan, LearningPlan, PlanTask

_PATTERN_NAMES = {p["id"]: p["name"] for p in DSA_PATTERNS}


@lru_cache(maxsize=1)
def _load_raw(path_str: str) -> tuple[dict, ...]:
    path = Path(path_str)
    if not path.exists():
        return ()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return ()
    companies = data.get("companies", []) if isinstance(data, dict) else data
    return tuple(c for c in companies if isinstance(c, dict) and c.get("id") and c.get("name"))


def load_companies(path: Path | None = None) -> list[dict]:
    """All known company profiles, in dataset order."""
    return list(_load_raw(str(path or COMPANIES_DATA_FILE)))


def get_company(company_id: str, path: Path | None = None) -> dict | None:
    for c in load_companies(path):
        if c["id"] == company_id:
            return c
    return None


def search_companies(query: str, path: Path | None = None) -> list[dict]:
    """Case-insensitive substring match on name and aliases."""
    companies = load_companies(path)
    query = query.strip().lower()
    if not query:
        return companies
    results = []
    for c in companies:
        haystacks = [c["name"].lower()] + [a.lower() for a in c.get("aliases", [])]
        if any(query in h for h in haystacks):
            results.append(c)
    return results


def find_company_by_name(name: str, path: Path | None = None) -> dict | None:
    """Exact-ish match for free-text company fields (JD screen integration)."""
    name = name.strip().lower()
    if not name:
        return None
    for c in load_companies(path):
        candidates = [c["id"], c["name"].lower()] + [a.lower() for a in c.get("aliases", [])]
        if name in candidates:
            return c
    return None


def company_goal_text(company: dict, duration_days: int) -> str:
    """Natural-language goal used when the LLM generates the company plan."""
    patterns = ", ".join(
        _PATTERN_NAMES.get(p, p.replace("_", " ")) for p in company.get("patterns", [])
    )
    focus = "; ".join(company.get("focus_areas", [])[:3])
    return (
        f"Prepare me for a {company['name']} software engineering interview in "
        f"{duration_days} days. Emphasize their common patterns ({patterns}) and "
        f"focus areas ({focus}). Typical round length is "
        f"{company.get('typical_time_limit_min', 45)} minutes."
    )


def company_intelligence_note(company: dict) -> str:
    """Context block appended to JD problem generation for a known company."""
    lines = [f"Known interview intelligence for {company['name']}:"]
    if company.get("patterns"):
        lines.append(
            "- Common patterns: "
            + ", ".join(_PATTERN_NAMES.get(p, p) for p in company["patterns"])
        )
    if company.get("focus_areas"):
        lines.append("- Focus areas: " + "; ".join(company["focus_areas"]))
    if company.get("notes"):
        lines.append(f"- Notes: {company['notes']}")
    return "\n".join(lines)


def build_company_plan(company: dict, duration_days: int) -> LearningPlan:
    """Deterministic targeted plan from the company profile (works LLM-offline).

    Cycles the company's signature patterns and samples difficulty from its
    published distribution so harder-bar companies produce harder schedules.
    """
    patterns = company.get("patterns") or [p["id"] for p in DSA_PATTERNS[:5]]
    difficulties = _difficulty_cycle(company.get("difficulty_distribution", {}), duration_days)

    days = []
    for i in range(1, duration_days + 1):
        pattern = patterns[(i - 1) % len(patterns)]
        pattern_name = _PATTERN_NAMES.get(pattern, pattern.replace("_", " ").title())
        difficulty = difficulties[i - 1]
        minutes = company.get("typical_time_limit_min", 45)
        days.append(DayPlan(
            day_number=i,
            theme=f"{company['name']} prep — {pattern_name}",
            objectives=[
                f"Drill {pattern_name} at {difficulty} difficulty",
                f"Simulate a {minutes}-minute {company['name']} round",
            ],
            tasks=[PlanTask(
                type="problem",
                title=f"{pattern_name} ({company['name']} style)",
                problem_category="dsa",
                problem_subcategory=pattern,
                difficulty=difficulty,
                estimated_minutes=minutes,
            )],
            estimated_minutes=minutes,
        ))

    return LearningPlan(
        title=f"{company['name']} Interview Prep ({duration_days} days)",
        natural_language_goal=company_goal_text(company, duration_days),
        duration_days=duration_days,
        daily_schedule=days,
    )


def _difficulty_cycle(distribution: dict, n: int) -> list[str]:
    """Deterministic difficulty sequence roughly matching the distribution."""
    weights = {
        "easy": float(distribution.get("easy", 0.2)),
        "medium": float(distribution.get("medium", 0.6)),
        "hard": float(distribution.get("hard", 0.2)),
    }
    total = sum(weights.values()) or 1.0
    counts = {k: round(v / total * n) for k, v in weights.items()}
    # Fix rounding drift on the dominant bucket
    drift = n - sum(counts.values())
    counts["medium"] += drift

    sequence: list[str] = (
        ["easy"] * max(0, counts["easy"])
        + ["medium"] * max(0, counts["medium"])
        + ["hard"] * max(0, counts["hard"])
    )
    return sequence[:n] if len(sequence) >= n else sequence + ["medium"] * (n - len(sequence))
