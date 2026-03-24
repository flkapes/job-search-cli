"""Orchestrates problem creation via LLM with fallback to static bank."""

from __future__ import annotations

from codepractice.core.models import Example, Problem, ProblemSource, Solution, UserProfile
from codepractice.llm.client import LLMClient, LLMError, extract_json
from codepractice.llm.prompts.problem_gen import (
    dsa_problem_prompt,
    freeform_questions_prompt,
    jd_problems_prompt,
    python_fundamentals_prompt,
    resume_problems_prompt,
)


class ProblemGeneratorService:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def generate_dsa(
        self,
        pattern: str,
        difficulty: str = "medium",
        profile: UserProfile | None = None,
    ) -> Problem | None:
        messages = dsa_problem_prompt(pattern, difficulty, profile)
        try:
            raw = self.client.chat_sync(messages, temperature=0.8)
            return self._parse_single(raw, "dsa", pattern, difficulty, ProblemSource.ai_generated)
        except (LLMError, Exception):
            return None

    def generate_python_fundamental(
        self,
        topic: str,
        subtopic: str,
        difficulty: str = "medium",
        profile: UserProfile | None = None,
    ) -> Problem | None:
        messages = python_fundamentals_prompt(topic, subtopic, difficulty, profile)
        try:
            raw = self.client.chat_sync(messages, temperature=0.8)
            return self._parse_single(raw, "python_fundamentals", subtopic, difficulty, ProblemSource.ai_generated)
        except (LLMError, Exception):
            return None

    def generate_from_jd(
        self,
        jd_text: str,
        count: int = 5,
        profile: UserProfile | None = None,
    ) -> list[Problem]:
        messages = jd_problems_prompt(jd_text, count, profile)
        try:
            raw = self.client.chat_sync(messages, temperature=0.75)
            return self._parse_list(raw, "practical", "jd", "medium", ProblemSource.jd_driven)
        except (LLMError, Exception):
            return []

    def generate_from_resume(
        self,
        resume_parsed: dict,
        difficulty: str = "medium",
        count: int = 5,
    ) -> list[Problem]:
        messages = resume_problems_prompt(resume_parsed, difficulty, count)
        try:
            raw = self.client.chat_sync(messages, temperature=0.75)
            return self._parse_list(raw, "practical", "resume", difficulty, ProblemSource.resume_driven)
        except (LLMError, Exception):
            return []

    def generate_freeform_questions(
        self,
        source: str,
        text: str,
        question_types: list[str],
        count: int = 5,
    ) -> list[dict]:
        """
        Generate freeform interview questions (not coding problems).
        Returns a list of {"question": str, "type": str, "follow_ups": [str]}.
        """
        messages = freeform_questions_prompt(source, text, question_types, count)
        try:
            raw = self.client.chat_sync(messages, temperature=0.75)
            data = extract_json(raw)
            if not isinstance(data, list):
                return []
            result = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                question = item.get("question", "").strip()
                if not question:
                    continue
                result.append({
                    "question": question,
                    "type": str(item.get("type", "general")),
                    "follow_ups": [str(f) for f in item.get("follow_ups", []) if f],
                })
            return result
        except (LLMError, Exception):
            return []

    # ── Parsing helpers ────────────────────────────────────────────────────────

    def _parse_single(
        self, raw: str, category: str, subcategory: str, difficulty: str, source: ProblemSource
    ) -> Problem | None:
        data = extract_json(raw)
        if not isinstance(data, dict):
            return None
        return self._dict_to_problem(data, category, subcategory, difficulty, source)

    def _parse_list(
        self, raw: str, category: str, subcategory: str, difficulty: str, source: ProblemSource
    ) -> list[Problem]:
        data = extract_json(raw)
        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                return []
        problems = []
        for item in data:
            if isinstance(item, dict):
                p = self._dict_to_problem(item, category, subcategory, difficulty, source)
                if p:
                    problems.append(p)
        return problems

    @staticmethod
    def _dict_to_problem(
        data: dict, category: str, subcategory: str, difficulty: str, source: ProblemSource
    ) -> Problem | None:
        if not data.get("title") or not data.get("description"):
            return None
        examples = [
            Example(
                input=str(e.get("input", "")),
                output=str(e.get("output", "")),
                explanation=str(e.get("explanation", "")),
            )
            for e in data.get("examples", [])
            if isinstance(e, dict)
        ]
        solution_data = data.get("solution")
        solution = None
        if isinstance(solution_data, dict):
            solution = Solution(
                code=solution_data.get("code", ""),
                explanation=solution_data.get("explanation", ""),
                time_complexity=solution_data.get("time_complexity", "O(?)"),
                space_complexity=solution_data.get("space_complexity", "O(?)"),
            )
        return Problem(
            source=source,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty,
            title=data["title"],
            description=data["description"],
            constraints=data.get("constraints", ""),
            examples=examples,
            hints=data.get("hints", []),
            solution=solution,
            tags=data.get("tags", []),
        )
