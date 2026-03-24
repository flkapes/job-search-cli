"""Shared system prompt and context builders."""

from __future__ import annotations

from codepractice.core.models import UserProfile

SYSTEM_PROMPT = """You are CodeCoach, an expert programming mentor and coding interview coach.
You help developers practice Python, data structures & algorithms, and prepare for technical interviews.
You are encouraging, precise, and focus on teaching fundamentals deeply.
Always respond with valid JSON when asked for structured output — no commentary outside the JSON block."""


def build_profile_context(profile: UserProfile | None) -> str:
    if not profile or not profile.name:
        return ""
    lines = [f"Learner: {profile.name}"]
    if profile.experience_level:
        lines.append(f"Experience: {profile.experience_level.value}")
    if profile.target_role:
        lines.append(f"Target role: {profile.target_role}")
    if profile.resume_parsed.skills:
        lines.append(f"Known skills: {', '.join(profile.resume_parsed.skills[:15])}")
    if profile.resume_parsed.languages:
        lines.append(f"Languages: {', '.join(profile.resume_parsed.languages)}")
    return "\n".join(lines)


def system_message(extra: str = "") -> dict:
    content = SYSTEM_PROMPT
    if extra:
        content = f"{content}\n\n{extra}"
    return {"role": "system", "content": content}


def user_message(content: str) -> dict:
    return {"role": "user", "content": content}


def assistant_message(content: str) -> dict:
    return {"role": "assistant", "content": content}
