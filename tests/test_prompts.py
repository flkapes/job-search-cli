"""Tests for LLM prompt builder functions."""

from __future__ import annotations

from codepractice.core.models import Example, Problem, UserProfile
from codepractice.llm.prompts.base import (
    SYSTEM_PROMPT,
    assistant_message,
    build_profile_context,
    system_message,
    user_message,
)
from codepractice.llm.prompts.chat import build_chat_system_prompt, build_resume_analysis_prompt
from codepractice.llm.prompts.evaluator import evaluate_prompt, quick_check_prompt
from codepractice.llm.prompts.problem_gen import (
    dsa_problem_prompt,
    jd_problems_prompt,
    python_fundamentals_prompt,
    resume_problems_prompt,
)

# ── base.py ───────────────────────────────────────────────────────────────────

class TestBasePrompts:
    def test_system_prompt_defined(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 20

    def test_system_message_structure(self):
        msg = system_message()
        assert msg["role"] == "system"
        assert SYSTEM_PROMPT in msg["content"]

    def test_system_message_with_extra(self):
        msg = system_message("Extra context here")
        assert "Extra context here" in msg["content"]
        assert SYSTEM_PROMPT in msg["content"]

    def test_user_message(self):
        msg = user_message("Hello!")
        assert msg == {"role": "user", "content": "Hello!"}

    def test_assistant_message(self):
        msg = assistant_message("Hi there!")
        assert msg == {"role": "assistant", "content": "Hi there!"}

    def test_build_profile_context_none(self):
        assert build_profile_context(None) == ""

    def test_build_profile_context_no_name(self):
        profile = UserProfile(name="")
        assert build_profile_context(profile) == ""

    def test_build_profile_context_full(self):
        profile = UserProfile(
            name="Alice",
            target_role="Senior SWE",
            experience_level="senior",
        )
        ctx = build_profile_context(profile)
        assert "Alice" in ctx
        assert "senior" in ctx
        assert "Senior SWE" in ctx

    def test_build_profile_context_with_skills(self):
        from codepractice.core.models import ResumeParsed
        profile = UserProfile(
            name="Bob",
            resume_parsed=ResumeParsed(skills=["Python", "Go"], languages=["Python"]),
        )
        ctx = build_profile_context(profile)
        assert "Python" in ctx


# ── chat.py ───────────────────────────────────────────────────────────────────

class TestChatPrompts:
    def test_build_chat_system_prompt_minimal(self):
        msg = build_chat_system_prompt()
        assert msg["role"] == "system"
        assert isinstance(msg["content"], str)

    def test_build_chat_system_prompt_with_plan(self):
        msg = build_chat_system_prompt(active_plan_summary="30-day Python plan")
        assert "30-day Python plan" in msg["content"]
        assert "ACTIVE LEARNING PLAN" in msg["content"]

    def test_build_chat_system_prompt_with_performance(self):
        msg = build_chat_system_prompt(recent_performance="avg score: 0.7, weak: DP")
        assert "avg score" in msg["content"]

    def test_build_chat_system_prompt_with_profile(self):
        profile = UserProfile(name="Charlie", target_role="Backend Engineer")
        msg = build_chat_system_prompt(profile=profile)
        assert "Charlie" in msg["content"]

    def test_build_resume_analysis_prompt_structure(self):
        messages = build_resume_analysis_prompt("5 years Python, built Django apps")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "resume" in messages[1]["content"].lower()

    def test_resume_prompt_truncates_long_text(self):
        long_text = "x" * 10000
        messages = build_resume_analysis_prompt(long_text)
        user_content = messages[1]["content"]
        # The prompt caps at 4000 chars of resume text
        assert len(user_content) < 10000


# ── evaluator.py ──────────────────────────────────────────────────────────────

class TestEvaluatorPrompts:
    def _problem(self):
        return Problem(
            title="Two Sum",
            description="Find two numbers that add to target.",
            examples=[Example(input="[2,7], 9", output="[0,1]", explanation="2+7=9")],
        )

    def test_evaluate_prompt_structure(self):
        msgs = evaluate_prompt(self._problem(), "def solve(): pass", "My approach")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_evaluate_prompt_contains_problem_title(self):
        msgs = evaluate_prompt(self._problem(), "def solve(): pass", "")
        assert "Two Sum" in msgs[1]["content"]

    def test_evaluate_prompt_contains_code(self):
        msgs = evaluate_prompt(self._problem(), "def solve(): return []", "")
        assert "def solve(): return []" in msgs[1]["content"]

    def test_evaluate_prompt_with_test_results(self):
        msgs = evaluate_prompt(self._problem(), "def s(): pass", "", test_results="PASS: [0,1]")
        assert "PASS: [0,1]" in msgs[1]["content"]

    def test_quick_check_prompt_structure(self):
        msgs = quick_check_prompt(self._problem(), "def solve(): pass")
        assert len(msgs) == 2
        assert "score" in msgs[1]["content"].lower()

    def test_quick_check_prompt_contains_title(self):
        msgs = quick_check_prompt(self._problem(), "x = 1")
        assert "Two Sum" in msgs[1]["content"]


# ── problem_gen.py ────────────────────────────────────────────────────────────

class TestProblemGenPrompts:
    def test_dsa_problem_prompt_structure(self):
        msgs = dsa_problem_prompt("two_pointers", "medium")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_dsa_prompt_contains_pattern(self):
        msgs = dsa_problem_prompt("sliding_window", "easy")
        assert "sliding_window" in msgs[1]["content"]

    def test_dsa_prompt_contains_difficulty(self):
        msgs = dsa_problem_prompt("bfs", "hard")
        assert "hard" in msgs[1]["content"]

    def test_dsa_prompt_with_profile(self):
        profile = UserProfile(name="Dan", target_role="SWE")
        msgs = dsa_problem_prompt("dfs", "medium", profile=profile)
        assert "Dan" in msgs[1]["content"]

    def test_python_fundamentals_prompt_structure(self):
        msgs = python_fundamentals_prompt("OOP & Classes", "oop", "medium")
        assert len(msgs) == 2
        assert "oop" in msgs[1]["content"].lower()

    def test_python_prompt_uses_guidance_map(self):
        msgs = python_fundamentals_prompt("Core Vocabulary", "vocabulary", "easy")
        assert "comprehensions" in msgs[1]["content"] or "generators" in msgs[1]["content"]

    def test_python_prompt_unknown_subtopic_uses_topic(self):
        msgs = python_fundamentals_prompt("My Topic", "unknown_subtopic", "hard")
        assert "My Topic" in msgs[1]["content"]

    def test_jd_problems_prompt_structure(self):
        msgs = jd_problems_prompt("Looking for a Python engineer...", count=3)
        assert len(msgs) == 2
        assert "3" in msgs[1]["content"]

    def test_jd_prompt_truncates_long_jd(self):
        long_jd = "x" * 10000
        msgs = jd_problems_prompt(long_jd, count=2)
        user_content = msgs[1]["content"]
        assert len(user_content) < 10000

    def test_resume_problems_prompt_structure(self):
        resume = {
            "skills": ["Python", "Django"],
            "languages": ["Python"],
            "projects": [{"name": "MyApp", "description": "A web app"}],
        }
        msgs = resume_problems_prompt(resume, "medium", count=2)
        assert len(msgs) == 2
        assert "Python" in msgs[1]["content"]
        assert "MyApp" in msgs[1]["content"]

    def test_resume_prompt_handles_empty_resume(self):
        msgs = resume_problems_prompt({}, "easy", count=1)
        assert len(msgs) == 2  # should not crash
