"""Tests for deterministic verification in the answer evaluator."""

from __future__ import annotations

from typing import Generator

from codepractice.core.models import Example, Problem
from codepractice.llm.client import LLMClient, LLMError
from codepractice.llm.services.answer_evaluator import (
    AnswerEvaluatorService,
    format_verification,
)


class MockLLMClient(LLMClient):
    def __init__(self, response: str = "", fail: bool = False):
        self.response = response
        self.fail = fail
        self.last_messages: list[dict] | None = None

    def health_check(self) -> bool:
        return not self.fail

    def chat_sync(self, messages: list[dict], **kwargs) -> str:
        self.last_messages = messages
        if self.fail:
            raise LLMError("offline")
        return self.response

    def stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        self.last_messages = messages
        if self.fail:
            raise LLMError("offline")
        yield self.response


def _stdin_problem() -> Problem:
    return Problem(
        title="Double It",
        description="Read an integer from stdin and print it doubled.",
        examples=[
            Example(input="21", output="42"),
            Example(input="5", output="10"),
        ],
    )


class TestVerify:
    def test_correct_solution_fully_verified(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        summary = svc.verify(_stdin_problem(), "print(int(input()) * 2)")
        assert summary.fully_verified is True
        assert summary.passed == 2

    def test_wrong_solution_fails(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        summary = svc.verify(_stdin_problem(), "print(int(input()) * 3)")
        assert summary.failed == 2
        assert summary.all_passed is False

    def test_no_examples_indeterminate(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        problem = Problem(title="T", description="d")
        assert svc.verify(problem, "print(1)").indeterminate is True

    def test_empty_code_indeterminate(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        assert svc.verify(_stdin_problem(), "   ").indeterminate is True


class TestGuardrailsInEvaluateSync:
    def test_llm_high_score_capped_when_tests_fail(self):
        client = MockLLMClient('Looks great!\n{"score": 0.95, "passed": true}')
        svc = AnswerEvaluatorService(client)
        feedback = svc.evaluate_sync(_stdin_problem(), "print(int(input()) * 3)")
        assert feedback.passed is False
        assert feedback.overall_score <= 0.4

    def test_llm_borderline_fail_floored_when_fully_verified(self):
        client = MockLLMClient('Close but unsure.\n{"score": 0.55, "passed": false}')
        svc = AnswerEvaluatorService(client)
        feedback = svc.evaluate_sync(_stdin_problem(), "print(int(input()) * 2)")
        assert feedback.passed is True
        assert feedback.overall_score >= 0.7

    def test_emphatic_llm_fail_not_overruled_by_examples(self):
        """Hard-coding the printed examples must not force a pass."""
        client = MockLLMClient('Hard-coded outputs.\n{"score": 0.1, "passed": false}')
        svc = AnswerEvaluatorService(client)
        # Prints correct outputs for both examples without computing anything
        cheat = "import sys\nprint({'21': 42, '5': 10}[sys.stdin.read().strip()])"
        feedback = svc.evaluate_sync(_stdin_problem(), cheat)
        assert feedback.passed is False

    def test_test_results_included_in_prompt(self):
        client = MockLLMClient('ok\n{"score": 0.8, "passed": true}')
        svc = AnswerEvaluatorService(client)
        svc.evaluate_sync(_stdin_problem(), "print(int(input()) * 2)")
        prompt_text = "\n".join(m["content"] for m in client.last_messages)
        assert "PASS" in prompt_text


class TestOfflineFallback:
    def test_offline_uses_test_results_not_blanket_half(self):
        svc = AnswerEvaluatorService(MockLLMClient(fail=True))
        feedback = svc.evaluate_sync(_stdin_problem(), "print(int(input()) * 2)")
        assert feedback.passed is True
        assert feedback.overall_score == 1.0

    def test_offline_failing_code_scores_zero(self):
        svc = AnswerEvaluatorService(MockLLMClient(fail=True))
        feedback = svc.evaluate_sync(_stdin_problem(), "print(int(input()) * 3)")
        assert feedback.passed is False
        assert feedback.overall_score == 0.0

    def test_offline_indeterminate_falls_back_to_half(self):
        svc = AnswerEvaluatorService(MockLLMClient(fail=True))
        problem = Problem(title="T", description="d")
        feedback = svc.evaluate_sync(problem, "def f(): pass")
        assert feedback.overall_score == 0.5

    def test_stream_fallback_reflects_test_results(self):
        svc = AnswerEvaluatorService(MockLLMClient(fail=True))
        tokens = list(svc.stream_evaluation(_stdin_problem(), "print(int(input()) * 2)"))
        joined = "".join(tokens)
        assert '"passed": true' in joined


class TestFormatVerification:
    def test_empty_summary_formats_empty(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        problem = Problem(title="T", description="d")
        assert format_verification(svc.verify(problem, "x = 1")) == ""

    def test_failure_shows_expected_vs_actual(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        text = format_verification(svc.verify(_stdin_problem(), "print('nope')"))
        assert "FAIL" in text
        assert "expected" in text
        assert "nope" in text

    def test_pass_summary_line(self):
        svc = AnswerEvaluatorService(MockLLMClient())
        text = format_verification(svc.verify(_stdin_problem(), "print(int(input()) * 2)"))
        assert "2/2 passed" in text
