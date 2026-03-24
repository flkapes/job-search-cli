"""Conversational coach prompt builder."""

from __future__ import annotations

from codepractice.core.models import UserProfile
from codepractice.llm.prompts.base import build_profile_context, system_message


def build_chat_system_prompt(
    profile: UserProfile | None = None,
    active_plan_summary: str = "",
    recent_performance: str = "",
) -> dict:
    ctx = build_profile_context(profile)
    extra_parts = []

    if ctx:
        extra_parts.append(f"LEARNER PROFILE:\n{ctx}")
    if active_plan_summary:
        extra_parts.append(f"ACTIVE LEARNING PLAN:\n{active_plan_summary}")
    if recent_performance:
        extra_parts.append(f"RECENT PERFORMANCE:\n{recent_performance}")

    extra = "\n\n".join(extra_parts)
    extra += (
        "\n\nYou can help with: explaining concepts, reviewing code, answering Python questions, "
        "adjusting the learning plan, suggesting next steps, or motivating the learner. "
        "Be conversational, specific, and actionable. Use markdown formatting."
    )

    return system_message(extra)


def build_resume_analysis_prompt(resume_text: str) -> list[dict]:
    return [
        system_message(),
        {
            "role": "user",
            "content": f"""Parse this resume and extract structured information.

RESUME:
{resume_text[:4000]}

Respond ONLY with valid JSON:
{{
  "skills": ["skill1", "skill2"],
  "languages": ["Python", "JavaScript"],
  "frameworks": ["Django", "React"],
  "years_experience": 3,
  "summary": "Brief 2-sentence summary of the developer",
  "projects": [
    {{
      "name": "Project name",
      "description": "What it does",
      "technologies": ["Python", "PostgreSQL"],
      "highlights": ["Key achievement or feature"]
    }}
  ]
}}""",
        },
    ]
