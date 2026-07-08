"""Evaluates user code/answers and returns structured feedback with streaming."""

from __future__ import annotations

from typing import Generator

from codepractice.core.models import AIFeedback, Problem
from codepractice.llm.client import LLMClient, LLMError, extract_json
from codepractice.llm.prompts.evaluator import evaluate_prompt, quick_check_prompt
from codepractice.utils.code_runner import (
    VerificationSummary,
    clamp_score,
    run_with_test_cases,
    summarize_results,
)


class AnswerEvaluatorService:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def verify(self, problem: Problem, user_code: str, language: str = "python") -> VerificationSummary:
        """Run the code against the problem's examples and verify output deterministically."""
        if not problem.examples or not user_code.strip():
            return VerificationSummary()
        cases = [
            {"input": e.input, "expected_output": e.output}
            for e in problem.examples[:3]
        ]
        return summarize_results(run_with_test_cases(user_code, cases, language=language))

    def stream_evaluation(
        self,
        problem: Problem,
        user_code: str,
        user_explanation: str = "",
        verification: VerificationSummary | None = None,
        language: str = "python",
    ) -> Generator[str, None, None]:
        """Stream the evaluation text. The last chunk will contain the score JSON."""
        if verification is None:
            verification = self.verify(problem, user_code, language=language)
        test_output = format_verification(verification)

        messages = evaluate_prompt(problem, user_code, user_explanation, test_output, language=language)
        try:
            yield from self.client.stream_chat(messages, temperature=0.3)
        except LLMError as e:
            yield f"\n\n[Evaluation unavailable: {e}]"
            fallback = self._offline_feedback(verification)
            yield f'\n{{"score": {fallback.overall_score}, "passed": {"true" if fallback.passed else "false"}}}'

    def evaluate_sync(
        self,
        problem: Problem,
        user_code: str,
        user_explanation: str = "",
        language: str = "python",
    ) -> AIFeedback:
        """Blocking evaluation — returns structured feedback with test guardrails applied."""
        verification = self.verify(problem, user_code, language=language)
        test_output = format_verification(verification)
        messages = evaluate_prompt(problem, user_code, user_explanation, test_output, language=language)
        try:
            raw = self.client.chat_sync(messages, temperature=0.3)
            feedback = self._parse_feedback(raw)
        except LLMError:
            return self._offline_feedback(verification)

        score, passed = clamp_score(feedback.overall_score, feedback.passed, verification)
        if (score, passed) != (feedback.overall_score, feedback.passed):
            feedback = AIFeedback.from_score(score, feedback.explanation)
            feedback.passed = passed
        return feedback

    def quick_score(self, problem: Problem, user_code: str) -> AIFeedback:
        """Fast scoring without detailed explanation."""
        messages = quick_check_prompt(problem, user_code)
        try:
            raw = self.client.chat_sync(messages, temperature=0.1)
            data = extract_json(raw)
            if isinstance(data, dict):
                score = float(data.get("score", 0.5))
                feedback = data.get("one_line_feedback", "")
                return AIFeedback.from_score(score, feedback)
        except (LLMError, Exception):
            pass
        return AIFeedback.from_score(0.5, "Quick check unavailable")

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _offline_feedback(verification: VerificationSummary) -> AIFeedback:
        """Score from deterministic test results when the LLM is unreachable."""
        if verification.indeterminate:
            return AIFeedback.from_score(0.5, "Evaluation unavailable (LLM offline)")
        score = round(verification.pass_rate, 2)
        fb = AIFeedback.from_score(
            score,
            f"LLM offline — scored from test cases: "
            f"{verification.passed}/{verification.comparable} passed.",
        )
        fb.passed = verification.all_passed
        return fb

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


def format_verification(summary: VerificationSummary) -> str:
    """Render a verification summary for LLM prompts and logs."""
    if summary.total == 0:
        return ""
    lines = []
    for i, r in enumerate(summary.results, 1):
        if not r.comparable:
            status = "SKIP (output not verifiable)"
        elif r.passed:
            status = "PASS"
        else:
            status = "FAIL"
        line = f"Case {i}: {status}"
        if r.comparable and not r.passed:
            if r.error:
                line += f" | error: {r.error} {r.stderr[:150]}".rstrip()
            else:
                line += f" | expected: {r.expected[:120]!r} | actual: {r.actual[:120]!r}"
        lines.append(line)
    lines.append(
        f"Verified: {summary.passed}/{summary.comparable} passed"
        + (" (some cases not verifiable via stdout)" if summary.comparable < summary.total else "")
    )
    return "\n".join(lines)
