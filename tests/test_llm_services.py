"""Tests for LLM services using a mock client (no real LLM required)."""

from __future__ import annotations

from typing import Generator

import pytest

from codepractice.core.models import AIFeedback, DayPlan, LearningPlan, Problem
from codepractice.llm.client import LLMClient, LLMError
from codepractice.llm.services.answer_evaluator import AnswerEvaluatorService
from codepractice.llm.services.plan_manager import LearningPlanManager as PlanManagerService

# ── Mock LLM Client ────────────────────────────────────────────────────────────

class MockLLMClient(LLMClient):
    """Configurable mock that returns preset responses."""

    def __init__(self, response: str = "", stream_tokens: list[str] | None = None, fail: bool = False):
        self._response = response
        self._stream_tokens = stream_tokens or [response]
        self._fail = fail
        self.model = "mock-model"
        self.base_url = "http://mock"

    def health_check(self) -> bool:
        return not self._fail

    def list_models(self) -> list[str]:
        return ["mock-model"]

    def chat_sync(self, messages: list[dict], **kwargs) -> str:
        if self._fail:
            raise LLMError("mock failure")
        return self._response

    def stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        if self._fail:
            raise LLMError("mock stream failure")
        yield from self._stream_tokens


def _problem(title: str = "Test Problem") -> Problem:
    return Problem(title=title, description="Solve this efficiently.", category="dsa")


# ── AnswerEvaluatorService ────────────────────────────────────────────────────

class TestAnswerEvaluatorService:
    def test_stream_evaluation_yields_tokens(self):
        client = MockLLMClient(stream_tokens=["Good ", "solution! ", '{"score": 0.85}'])
        svc = AnswerEvaluatorService(client)
        tokens = list(svc.stream_evaluation(_problem(), "def solve(): return 42"))
        assert len(tokens) > 0
        full = "".join(tokens)
        assert "Good" in full

    def test_stream_evaluation_llm_failure_yields_fallback(self):
        client = MockLLMClient(fail=True)
        svc = AnswerEvaluatorService(client)
        tokens = list(svc.stream_evaluation(_problem(), "def solve(): pass"))
        full = "".join(tokens)
        assert "unavailable" in full.lower() or "0.5" in full

    def test_evaluate_sync_returns_feedback(self):
        response = 'Great work!\n{"score": 0.9, "passed": true}'
        client = MockLLMClient(response=response)
        svc = AnswerEvaluatorService(client)
        feedback = svc.evaluate_sync(_problem(), "def solve(): return 42")
        assert isinstance(feedback, AIFeedback)

    def test_evaluate_sync_llm_failure_returns_fallback(self):
        client = MockLLMClient(fail=True)
        svc = AnswerEvaluatorService(client)
        feedback = svc.evaluate_sync(_problem(), "def solve(): pass")
        assert isinstance(feedback, AIFeedback)
        assert feedback.overall_score == 0.5

    def test_parse_feedback_extracts_score(self):
        raw = "Analysis here.\n\n{'score': 0.75, 'passed': true}\n"
        feedback = AnswerEvaluatorService._parse_feedback(raw)
        assert isinstance(feedback, AIFeedback)

    def test_parse_feedback_no_json_returns_default(self):
        raw = "Just some plain text evaluation with no JSON."
        feedback = AnswerEvaluatorService._parse_feedback(raw)
        assert isinstance(feedback, AIFeedback)
        assert feedback.overall_score == 0.5

    def test_parse_feedback_with_embedded_json(self):
        raw = 'Nice work!\n{"score": 0.8, "passed": true}'
        feedback = AnswerEvaluatorService._parse_feedback(raw)
        assert feedback.overall_score == pytest.approx(0.8)
        assert feedback.passed is True


# ── PlanManagerService ────────────────────────────────────────────────────────

class TestPlanManagerService:
    def test_default_plan_structure(self):
        plan = PlanManagerService._default_plan("Prepare for FAANG", duration_days=10)
        assert isinstance(plan, LearningPlan)
        assert plan.duration_days == 10
        assert len(plan.daily_schedule) == 10

    def test_default_plan_title_from_goal(self):
        plan = PlanManagerService._default_plan("Learn dynamic programming", duration_days=5)
        assert "Learn dynamic programming" in plan.title or "5-Day" in plan.title

    def test_default_plan_long_goal_truncated(self):
        long_goal = "x" * 200
        plan = PlanManagerService._default_plan(long_goal, duration_days=3)
        assert len(plan.title) <= 63  # 60 + possible suffix

    def test_default_plan_cycles_topics(self):
        plan = PlanManagerService._default_plan("goal", duration_days=15)
        themes = [d.theme for d in plan.daily_schedule]
        # Should cycle through multiple topics
        assert len(set(themes)) > 1

    def test_default_plan_all_days_have_tasks(self):
        plan = PlanManagerService._default_plan("goal", duration_days=7)
        for day in plan.daily_schedule:
            assert len(day.tasks) > 0

    def test_parse_day_with_tasks(self):
        data = {
            "day_number": 3,
            "theme": "Dynamic Programming",
            "objectives": ["Understand memoization"],
            "estimated_minutes": 60,
            "tasks": [
                {
                    "type": "problem",
                    "title": "Fibonacci",
                    "problem_category": "dsa",
                    "difficulty": "medium",
                    "estimated_minutes": 30,
                }
            ],
        }
        day = PlanManagerService._parse_day(data)
        assert isinstance(day, DayPlan)
        assert day.day_number == 3
        assert day.theme == "Dynamic Programming"
        assert len(day.tasks) == 1
        assert day.tasks[0].title == "Fibonacci"

    def test_parse_day_empty_tasks(self):
        data = {"day_number": 1, "theme": "Intro", "tasks": []}
        day = PlanManagerService._parse_day(data)
        assert day.tasks == []

    def test_create_plan_llm_failure_returns_default(self):
        client = MockLLMClient(fail=True)
        svc = PlanManagerService(client)
        plan = svc.create_plan("Prepare for interviews", duration_days=7)
        assert isinstance(plan, LearningPlan)
        assert plan.duration_days == 7

    def test_create_plan_success_returns_plan(self):
        client = MockLLMClient(fail=True)  # will use default plan fallback
        svc = PlanManagerService(client)
        plan = svc.create_plan("Learn Python", duration_days=5)
        assert plan is not None
        assert len(plan.daily_schedule) == 5
