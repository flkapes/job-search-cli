"""Problem generation prompt templates."""

from __future__ import annotations

from codepractice.core.models import UserProfile
from codepractice.llm.prompts.base import build_profile_context, system_message, user_message

_PROBLEM_SCHEMA = """{
  "title": "string",
  "description": "string (markdown supported, include context and goal)",
  "constraints": "string (input size, edge cases)",
  "examples": [
    {"input": "string", "output": "string", "explanation": "string"}
  ],
  "hints": ["hint1", "hint2", "hint3"],
  "solution": {
    "code": "python code string",
    "explanation": "string",
    "time_complexity": "O(...)",
    "space_complexity": "O(...)"
  },
  "tags": ["tag1", "tag2"]
}"""


def dsa_problem_prompt(
    pattern: str,
    difficulty: str,
    profile: UserProfile | None = None,
) -> list[dict]:
    ctx = build_profile_context(profile)
    return [
        system_message(),
        user_message(
            f"""Generate a {difficulty} coding problem that practices the **{pattern}** pattern.
{f'Context: {ctx}' if ctx else ''}

Requirements:
- The problem must clearly require {pattern} to solve optimally
- Include 2-3 concrete examples with explanations
- Provide 3 progressive hints (don't give away the approach immediately)
- Include a clean Python solution with complexity analysis

Respond ONLY with valid JSON matching this schema:
{_PROBLEM_SCHEMA}"""
        ),
    ]


def python_fundamentals_prompt(
    topic: str,
    subtopic: str,
    difficulty: str,
    profile: UserProfile | None = None,
) -> list[dict]:
    ctx = build_profile_context(profile)
    topic_guidance = {
        "vocabulary": "comprehensions, generators, decorators, context managers, or core Python concepts",
        "builtins": "built-in functions like map, filter, zip, sorted, enumerate, or functools/itertools",
        "oop": "classes, inheritance, dunder methods, dataclasses, abstract base classes, or properties",
        "threading": "threading.Thread, Lock, Queue, concurrent.futures, or asyncio",
        "version_control": "git concepts (framed as a coding/conceptual challenge, not terminal commands)",
        "patterns": "design patterns like Singleton, Observer, Factory, or Strategy implemented in Python",
    }
    guidance = topic_guidance.get(subtopic, topic)

    return [
        system_message(),
        user_message(
            f"""Generate a {difficulty} Python practice problem about **{topic} — {subtopic}**.
Focus area: {guidance}
{f'Context: {ctx}' if ctx else ''}

The problem should:
- Test deep understanding, not just syntax recall
- Include a runnable code example or implementation challenge
- Be practical and applicable to real-world Python code

Respond ONLY with valid JSON matching this schema:
{_PROBLEM_SCHEMA}"""
        ),
    ]


def jd_problems_prompt(
    jd_text: str,
    count: int,
    profile: UserProfile | None = None,
) -> list[dict]:
    ctx = build_profile_context(profile)
    return [
        system_message(),
        user_message(
            f"""Analyze this job description and generate {count} practical coding problems that prepare a candidate for this role.

JOB DESCRIPTION:
{jd_text[:3000]}

{f'Candidate context: {ctx}' if ctx else ''}

Focus on:
- Practical skills mentioned in the JD (frameworks, tools, problem domains)
- Real-world coding tasks they'll likely do on the job
- NOT just abstract DSA puzzles — make them domain-relevant

Respond ONLY with valid JSON as an array of {count} problems:
[{_PROBLEM_SCHEMA}, ...]"""
        ),
    ]


def resume_problems_prompt(
    resume_parsed: dict,
    difficulty: str,
    count: int,
) -> list[dict]:
    skills = resume_parsed.get("skills", [])
    projects = resume_parsed.get("projects", [])
    languages = resume_parsed.get("languages", [])

    project_summaries = "\n".join(
        f"- {p.get('name', '')}: {p.get('description', '')[:150]}"
        for p in projects[:5]
    )

    return [
        system_message(),
        user_message(
            f"""Generate {count} {difficulty} coding problems tailored to this developer's background.

Skills: {', '.join(skills[:20])}
Languages: {', '.join(languages)}
Projects:
{project_summaries}

The problems should:
- Reinforce concepts they've used in their projects
- Help them speak more confidently about their resume
- Mix implementation challenges with conceptual depth

Respond ONLY with valid JSON as an array of {count} problems:
[{_PROBLEM_SCHEMA}, ...]"""
        ),
    ]
