"""Orchestrates problem creation via LLM with fallback to static bank.

Generated coding problems follow the same contract as the bundled bank: the
model must return a complete stdin/stdout program as the reference solution,
and that solution is executed against the problem's own examples. Problems
whose solutions don't reproduce their examples are rejected rather than
saved, so everything in the database is verifiable.
"""

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

GENERATION_MAX_TOKENS = 8192


class ProblemGeneratorService:
    def __init__(self, client: LLMClient, validate: bool = True) -> None:
        self.client = client
        self.validate = validate

    def generate_dsa(
        self,
        pattern: str,
        difficulty: str = "medium",
        profile: UserProfile | None = None,
    ) -> Problem | None:
        messages = dsa_problem_prompt(pattern, difficulty, profile)
        try:
            raw = self.client.chat_sync(messages, temperature=0.8, max_tokens=GENERATION_MAX_TOKENS)
            problem = self._parse_single(raw, "dsa", pattern, difficulty, ProblemSource.ai_generated)
            return problem if self._acceptable(problem) else None
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
            raw = self.client.chat_sync(messages, temperature=0.8, max_tokens=GENERATION_MAX_TOKENS)
            problem = self._parse_single(raw, "python_fundamentals", subtopic, difficulty, ProblemSource.ai_generated)
            return problem if self._acceptable(problem) else None
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
            raw = self.client.chat_sync(messages, temperature=0.75, max_tokens=GENERATION_MAX_TOKENS)
            problems = self._parse_list(raw, "practical", "jd", "medium", ProblemSource.jd_driven)
            return [p for p in problems if self._acceptable(p)]
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
            raw = self.client.chat_sync(messages, temperature=0.75, max_tokens=GENERATION_MAX_TOKENS)
            problems = self._parse_list(raw, "practical", "resume", difficulty, ProblemSource.resume_driven)
            return [p for p in problems if self._acceptable(p)]
        except (LLMError, Exception):
            return []

    # ── Validation ─────────────────────────────────────────────────────────────

    def _acceptable(self, problem: Problem | None) -> bool:
        if problem is None:
            return False
        if not self.validate:
            return True
        return self.is_verified(problem)

    @staticmethod
    def is_verified(problem: Problem) -> bool:
        """Run the generated reference solution against the problem's examples.

        A generated problem is only trustworthy if its own solution reproduces
        every example exactly — the same guarantee the bundled bank carries.
        """
        if not problem.solution or not problem.solution.code.strip():
            return False
        cases = [
            {"input": e.input, "expected_output": e.output}
            for e in problem.examples
            if e.output.strip()
        ]
        if len(cases) < 2:
            return False
        from codepractice.utils.code_runner import run_with_test_cases, summarize_results

        summary = summarize_results(
            run_with_test_cases(problem.solution.code, cases, timeout=15)
        )
        return summary.fully_verified

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
