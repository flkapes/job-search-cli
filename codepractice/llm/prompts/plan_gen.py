"""Learning plan generation and evolution prompts."""

from __future__ import annotations

from codepractice.core.models import UserProfile
from codepractice.llm.prompts.base import build_profile_context, system_message, user_message

_DAY_SCHEMA = """{
  "day_number": 1,
  "theme": "Arrays & Hashing",
  "objectives": ["Understand hash maps", "Practice O(1) lookup patterns"],
  "tasks": [
    {
      "type": "problem",
      "title": "Two Sum",
      "description": "Classic hash map problem",
      "problem_category": "dsa",
      "problem_subcategory": "hash_map",
      "difficulty": "easy",
      "estimated_minutes": 20
    }
  ],
  "estimated_minutes": 45
}"""


def create_plan_prompt(
    goal: str,
    duration_days: int,
    profile: UserProfile | None = None,
    weak_areas: list[str] | None = None,
) -> list[dict]:
    ctx = build_profile_context(profile)
    weak_str = f"Weak areas to address: {', '.join(weak_areas)}" if weak_areas else ""

    return [
        system_message(),
        user_message(
            f"""Create a structured {duration_days}-day learning plan for this goal:

GOAL: {goal}

{f'Learner profile: {ctx}' if ctx else ''}
{weak_str}

Requirements:
- Each day should have a clear theme and 1-3 focused tasks
- Mix problem-solving practice with conceptual review
- Ramp difficulty progressively
- Days near the end should be review/mock sessions
- Keep daily time commitment to 45-90 minutes

Respond with valid JSON:
{{
  "title": "Plan title",
  "summary": "2-3 sentence overview",
  "daily_schedule": [
    {_DAY_SCHEMA},
    ... (all {duration_days} days)
  ]
}}"""
        ),
    ]


def evolve_plan_prompt(
    plan_title: str,
    original_goal: str,
    current_day: int,
    days_remaining: int,
    performance_summary: str,
    weak_areas: list[str],
) -> list[dict]:
    return [
        system_message(),
        user_message(
            f"""Update the remaining days of this learning plan based on recent performance.

Plan: {plan_title}
Original goal: {original_goal}
Current day: {current_day}, Days remaining: {days_remaining}

Performance summary:
{performance_summary}

Weak areas that need more focus: {', '.join(weak_areas) if weak_areas else 'none identified'}

Regenerate the remaining {days_remaining} days of the plan.
Keep what's working, add more practice on weak areas, reduce time on mastered topics.

Respond with valid JSON — array of {days_remaining} day objects:
[{_DAY_SCHEMA}, ...]"""
        ),
    ]


def daily_briefing_prompt(day_theme: str, objectives: list[str], profile: UserProfile | None) -> list[dict]:
    ctx = build_profile_context(profile)
    return [
        system_message(),
        user_message(
            f"""Write a brief, motivating daily briefing (3-4 sentences) for this practice session.

Today's theme: {day_theme}
Objectives: {', '.join(objectives)}
{f'Learner: {ctx}' if ctx else ''}

Be encouraging, specific, and set clear expectations for what they'll accomplish today.
Write in second person. No headers or bullet points — just flowing text."""
        ),
    ]
