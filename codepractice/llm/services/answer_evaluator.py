"""Evaluates user code/answers and returns structured feedback with streaming."""

from __future__ import annotations

import re
from typing import Generator

from codepractice.core.models import AIFeedback, Problem
from codepractice.llm.client import LLMClient, LLMError, extract_json
from codepractice.llm.prompts.evaluator import evaluate_prompt, quick_check_prompt
from codepractice.utils.code_runner import run_code


class AnswerEvaluatorService:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def stream_evaluation(
        self,
        problem: Problem,
        user_code: str,
        user_explanation: str = "",
    ) -> Generator[str, None, None]:
        """Stream the evaluation text. The last chunk will contain the score JSON."""
        # Run code against examples first
        test_output = self._run_tests(problem, user_code)

        messages = evaluate_prompt(problem, user_code, user_explanation, test_output)
        try:
            yield from self.client.stream_chat(messages, temperature=0.3)
        except LLMError as e:
            yield f"\n\n[Evaluation unavailable: {e}]"
            yield '\n{"score": 0.5, "passed": false}'

    def evaluate_sync(
        self,
        problem: Problem,
        user_code: str,
        user_explanation: str = "",
    ) -> AIFeedback:
        """Blocking evaluation — returns structured feedback."""
        test_output = self._run_tests(problem, user_code)
        messages = evaluate_prompt(problem, user_code, user_explanation, test_output)
        try:
            raw = self.client.chat_sync(messages, temperature=0.3)
            return self._parse_feedback(raw)
        except LLMError:
            return AIFeedback.from_score(0.5, "Evaluation unavailable (LLM offline)")

    def quick_score(self, problem: Problem, user_code: str) -> AIFeedback:
        """Fast scoring without detailed explanation."""
        messages = quick_check_prompt(problem, user_code)
        try:
            raw = self.client.chat_sync(messages, temperature=0.1)
            data = extract_json(raw)
            if isinstance(data, dict):
                score = float(data.get("score", 0.5))
                passed = bool(data.get("passed", score >= 0.7))
                feedback = data.get("one_line_feedback", "")
                return AIFeedback.from_score(score, feedback)
        except (LLMError, Exception):
            pass
        return AIFeedback.from_score(0.5, "Quick check unavailable")

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _run_tests(problem: Problem, user_code: str) -> str:
        """Execute user code against problem examples and return a summary."""
        if not problem.examples or not user_code.strip():
            return ""
        results = []
        for example in problem.examples[:3]:
            result = run_code(user_code)
            status = "PASS" if result.passed else "FAIL"
            results.append(f"[{status}] stdout: {result.stdout[:200]} | err: {result.stderr[:100]}")
        return "\n".join(results)

    @staticmethod
    def _parse_feedback(raw: str) -> AIFeedback:
        """Extract score JSON from the last line of streamed evaluation."""
        # Look for the score JSON at end
        lines = raw.strip().split("\n")
        score_data = None
        for line in reversed(lines):
            data = extract_json(line)
            if isinstance(data, dict) and "score" in data:
                score_data = data
                break

        if score_data:
            score = float(score_data.get("score", 0.5))
            passed = bool(score_data.get("passed", score >= 0.7))
            explanation = raw.rsplit("\n", 1)[0].strip()
            fb = AIFeedback.from_score(score, explanation)
            fb.passed = passed
            return fb

        return AIFeedback.from_score(0.5, raw)
