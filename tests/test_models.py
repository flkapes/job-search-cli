"""Tests for Pydantic data models."""

from __future__ import annotations

import pytest

from codepractice.core.models import (
    AIFeedback,
    AppStats,
    Difficulty,
    DayPlan,
    Example,
    ExperienceLevel,
    LearningPlan,
    LLMBackend,
    PlanStatus,
    PlanTask,
    Problem,
    ProblemAttempt,
    ProblemCategory,
    ProblemSource,
    ResumeParsed,
    SessionType,
    Solution,
    UserProfile,
)


# ── Enum sanity ────────────────────────────────────────────────────────────────

class TestEnums:
    def test_difficulty_values(self):
        assert Difficulty.easy.value == "easy"
        assert Difficulty.medium.value == "medium"
        assert Difficulty.hard.value == "hard"

    def test_problem_category_values(self):
        assert ProblemCategory.dsa.value == "dsa"
        assert ProblemCategory.python_fundamentals.value == "python_fundamentals"
        assert ProblemCategory.practical.value == "practical"

    def test_session_type_values(self):
        assert SessionType.free.value == "free"
        assert SessionType.plan.value == "plan"

    def test_experience_level_values(self):
        assert ExperienceLevel.junior.value == "junior"
        assert ExperienceLevel.mid.value == "mid"
        assert ExperienceLevel.senior.value == "senior"

    def test_llm_backend_values(self):
        assert LLMBackend.ollama.value == "ollama"
        assert LLMBackend.lmstudio.value == "lmstudio"


# ── Problem model ──────────────────────────────────────────────────────────────

class TestProblem:
    def _make_problem_dict(self, **overrides):
        base = {
            "title": "Two Sum",
            "description": "Given an array, return indices of two numbers that add to target.",
            "category": "dsa",
            "subcategory": "two_pointers",
            "difficulty": "easy",
            "source": "static",
            "constraints": "2 <= n <= 100",
            "examples": [{"input": "[2,7,11,15], 9", "output": "[0,1]", "explanation": "2+7=9"}],
            "hints": ["Use a hash map"],
            "tags": ["array", "hash-table"],
        }
        base.update(overrides)
        return base

    def test_basic_construction(self):
        p = Problem(title="Test", description="Desc")
        assert p.title == "Test"
        assert p.description == "Desc"
        assert p.difficulty == Difficulty.medium
        assert p.id is None
        assert p.hints == []
        assert p.tags == []

    def test_from_db_roundtrip(self):
        raw = self._make_problem_dict()
        p = Problem.from_db(raw)
        assert p.title == "Two Sum"
        assert p.category == "dsa"
        assert p.difficulty == Difficulty.easy
        assert len(p.examples) == 1
        assert p.examples[0].input == "[2,7,11,15], 9"
        assert p.hints == ["Use a hash map"]

    def test_to_db_and_back(self):
        raw = self._make_problem_dict(id=42)
        p = Problem.from_db(raw)
        db_dict = p.to_db()
        assert db_dict["title"] == "Two Sum"
        assert db_dict["difficulty"] == "easy"
        assert db_dict["source"] == "static"
        assert isinstance(db_dict["examples"], list)

    def test_from_db_missing_optional_fields(self):
        """from_db should handle missing optional fields gracefully."""
        p = Problem.from_db({"title": "Min", "description": "Desc"})
        assert p.hints == []
        assert p.tags == []
        assert p.solution is None

    def test_from_db_with_solution(self):
        raw = self._make_problem_dict(solution={"code": "return x", "explanation": "simple"})
        p = Problem.from_db(raw)
        assert p.solution is not None
        assert p.solution.code == "return x"


# ── AIFeedback model ───────────────────────────────────────────────────────────

class TestAIFeedback:
    def test_from_score_passing(self):
        fb = AIFeedback.from_score(0.8)
        assert fb.passed is True
        assert fb.verdict == "partial"  # 0.8 < 0.85 so partial
        assert fb.overall_score == 0.8

    def test_from_score_correct(self):
        fb = AIFeedback.from_score(0.9)
        assert fb.passed is True
        assert fb.verdict == "correct"

    def test_from_score_incorrect(self):
        fb = AIFeedback.from_score(0.3)
        assert fb.passed is False
        assert fb.verdict == "incorrect"

    def test_from_score_boundary_pass(self):
        fb = AIFeedback.from_score(0.7)
        assert fb.passed is True

    def test_from_score_boundary_fail(self):
        fb = AIFeedback.from_score(0.69)
        assert fb.passed is False

    def test_from_score_partial_boundary(self):
        fb = AIFeedback.from_score(0.5)
        assert fb.verdict == "partial"

    def test_from_score_subscores_derived(self):
        fb = AIFeedback.from_score(1.0)
        assert fb.efficiency_score == pytest.approx(0.9)
        assert fb.style_score == pytest.approx(0.85)


# ── LearningPlan model ─────────────────────────────────────────────────────────

class TestLearningPlan:
    def test_progress_pct_empty(self):
        plan = LearningPlan(title="Plan", duration_days=30)
        assert plan.progress_pct == 0.0

    def test_progress_pct_partial(self):
        plan = LearningPlan(
            title="Plan",
            duration_days=10,
            daily_schedule=[
                DayPlan(day_number=1, completed=True),
                DayPlan(day_number=2, completed=True),
                DayPlan(day_number=3, completed=False),
                DayPlan(day_number=4, completed=False),
            ],
        )
        assert plan.progress_pct == pytest.approx(0.5)

    def test_progress_pct_all_done(self):
        plan = LearningPlan(
            title="Plan",
            duration_days=2,
            daily_schedule=[
                DayPlan(day_number=1, completed=True),
                DayPlan(day_number=2, completed=True),
            ],
        )
        assert plan.progress_pct == 1.0

    def test_today_returns_correct_day(self):
        plan = LearningPlan(
            title="Plan",
            current_day=2,
            daily_schedule=[
                DayPlan(day_number=1, theme="Arrays"),
                DayPlan(day_number=2, theme="Graphs"),
                DayPlan(day_number=3, theme="DP"),
            ],
        )
        assert plan.today is not None
        assert plan.today.theme == "Graphs"

    def test_today_none_when_no_match(self):
        plan = LearningPlan(title="Plan", current_day=5, daily_schedule=[])
        assert plan.today is None


# ── UserProfile model ──────────────────────────────────────────────────────────

class TestUserProfile:
    def test_from_db(self):
        row = {
            "name": "Alice",
            "resume_text": "5 years Python",
            "target_role": "Senior SWE",
            "experience_level": "senior",
            "llm_backend": "ollama",
            "llm_model": "llama3",
            "llm_base_url": "",
            "resume_parsed": {"skills": ["Python", "Go"], "years_experience": 5},
        }
        profile = UserProfile.from_db(row)
        assert profile.name == "Alice"
        assert profile.experience_level == ExperienceLevel.senior
        assert profile.resume_parsed.skills == ["Python", "Go"]

    def test_from_db_defaults(self):
        profile = UserProfile.from_db({"name": "Bob"})
        assert profile.experience_level == ExperienceLevel.mid
        assert profile.llm_backend == LLMBackend.ollama


# ── AppStats model ─────────────────────────────────────────────────────────────

class TestAppStats:
    def test_solve_rate_zero_attempts(self):
        stats = AppStats()
        assert stats.solve_rate == 0.0

    def test_solve_rate_calculation(self):
        stats = AppStats(total_attempts=10, total_solved=7)
        assert stats.solve_rate == pytest.approx(0.7)

    def test_solve_rate_perfect(self):
        stats = AppStats(total_attempts=5, total_solved=5)
        assert stats.solve_rate == 1.0
