"""Tests for ProblemGeneratorService using a mock LLM client."""

from __future__ import annotations

import json
from typing import Generator

from codepractice.core.models import Problem, ProblemSource
from codepractice.llm.client import LLMClient, LLMError
from codepractice.llm.services.problem_generator import ProblemGeneratorService


class MockLLMClient(LLMClient):
    def __init__(self, response: str = "", fail: bool = False):
        self._response = response
        self._fail = fail
        self.model = "mock"
        self.base_url = "http://mock"

    def health_check(self) -> bool:
        return not self._fail

    def list_models(self) -> list[str]:
        return ["mock"]

    def chat_sync(self, messages, **kwargs) -> str:
        if self._fail:
            raise LLMError("offline")
        return self._response

    def stream_chat(self, messages, **kwargs) -> Generator[str, None, None]:
        yield self._response


def _problem_json(**overrides) -> str:
    """A generated problem whose solution genuinely reproduces its examples."""
    base = {
        "title": "Two Sum",
        "description": "Read numbers and a target; print the two 0-based indices.\n\n**Input**: line 1 — numbers; line 2 — target.\n\n**Output**: the indices.",
        "constraints": "2 <= n <= 100",
        "examples": [
            {"input": "2 7 11\n9", "output": "0 1", "explanation": "2+7=9"},
            {"input": "1 3\n4", "output": "0 1", "explanation": "1+3=4"},
        ],
        "hints": ["Use a hash map"],
        "solution": {
            "code": (
                "import sys\n"
                "lines = sys.stdin.read().splitlines()\n"
                "nums = list(map(int, lines[0].split()))\n"
                "target = int(lines[1])\n"
                "seen = {}\n"
                "for i, x in enumerate(nums):\n"
                "    if target - x in seen:\n"
                "        print(seen[target - x], i)\n"
                "        break\n"
                "    seen[x] = i\n"
            ),
            "explanation": "Hash map of seen values.",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
        },
        "tags": ["array"],
    }
    base.update(overrides)
    return json.dumps(base)


class TestProblemGeneratorService:
    def test_generate_dsa_success(self):
        client = MockLLMClient(response=_problem_json())
        svc = ProblemGeneratorService(client)
        problem = svc.generate_dsa("two_pointers", "medium")
        assert isinstance(problem, Problem)
        assert problem.title == "Two Sum"
        assert problem.category == "dsa"

    def test_generate_dsa_llm_failure_returns_none(self):
        client = MockLLMClient(fail=True)
        svc = ProblemGeneratorService(client)
        assert svc.generate_dsa("bfs", "hard") is None

    def test_generate_python_fundamental_success(self):
        client = MockLLMClient(response=_problem_json(title="Decorator Pattern"))
        svc = ProblemGeneratorService(client)
        problem = svc.generate_python_fundamental("OOP", "oop", "medium")
        assert problem is not None
        assert problem.category == "python_fundamentals"

    def test_generate_python_failure_returns_none(self):
        client = MockLLMClient(fail=True)
        svc = ProblemGeneratorService(client)
        assert svc.generate_python_fundamental("OOP", "oop") is None

    def test_generate_from_jd_success(self):
        problems_json = json.dumps([
            {"title": "Rate Limiter", "description": "Implement a token bucket."},
            {"title": "DB Connection Pool", "description": "Build a connection pool."},
        ])
        client = MockLLMClient(response=problems_json)
        svc = ProblemGeneratorService(client)
        problems = svc.generate_from_jd("Looking for a backend engineer...", count=2)
        # Problems without title/description are filtered, partial results ok
        assert isinstance(problems, list)

    def test_generate_from_jd_llm_failure_returns_empty(self):
        client = MockLLMClient(fail=True)
        svc = ProblemGeneratorService(client)
        assert svc.generate_from_jd("JD text", count=3) == []

    def test_generate_from_resume_success(self):
        problems_json = json.dumps([
            {"title": "Django ORM Query", "description": "Optimize this query."}
        ])
        client = MockLLMClient(response=problems_json)
        svc = ProblemGeneratorService(client)
        problems = svc.generate_from_resume({"skills": ["Python", "Django"]}, "medium", 1)
        assert isinstance(problems, list)

    def test_generate_from_resume_failure_returns_empty(self):
        client = MockLLMClient(fail=True)
        svc = ProblemGeneratorService(client)
        assert svc.generate_from_resume({}, "easy", 2) == []


class TestParseSingle:
    def _svc(self):
        return ProblemGeneratorService(MockLLMClient())

    def test_valid_json_returns_problem(self):
        svc = self._svc()
        raw = _problem_json()
        problem = svc._parse_single(raw, "dsa", "arrays", "easy", ProblemSource.ai_generated)
        assert problem is not None
        assert problem.title == "Two Sum"

    def test_invalid_json_returns_none(self):
        svc = self._svc()
        assert svc._parse_single("not json", "dsa", "arrays", "easy", ProblemSource.ai_generated) is None

    def test_missing_title_returns_none(self):
        svc = self._svc()
        raw = json.dumps({"description": "No title here"})
        assert svc._parse_single(raw, "dsa", "arrays", "easy", ProblemSource.ai_generated) is None


class TestParseList:
    def _svc(self):
        return ProblemGeneratorService(MockLLMClient())

    def test_valid_array_returns_problems(self):
        svc = self._svc()
        raw = json.dumps([
            {"title": "P1", "description": "D1"},
            {"title": "P2", "description": "D2"},
        ])
        problems = svc._parse_list(raw, "dsa", "arrays", "medium", ProblemSource.jd_driven)
        assert len(problems) == 2

    def test_single_object_wrapped_in_list(self):
        svc = self._svc()
        raw = json.dumps({"title": "P1", "description": "D1"})
        problems = svc._parse_list(raw, "dsa", "arrays", "medium", ProblemSource.jd_driven)
        assert len(problems) == 1

    def test_invalid_json_returns_empty(self):
        svc = self._svc()
        assert svc._parse_list("garbage", "dsa", "arrays", "easy", ProblemSource.jd_driven) == []

    def test_filters_incomplete_items(self):
        svc = self._svc()
        raw = json.dumps([
            {"title": "Good", "description": "Has both"},
            {"title": "No description"},  # missing description
            {"description": "No title"},  # missing title
        ])
        problems = svc._parse_list(raw, "dsa", "a", "easy", ProblemSource.ai_generated)
        assert len(problems) == 1
        assert problems[0].title == "Good"


class TestDictToProblem:
    def test_full_problem_dict(self):
        data = {
            "title": "Binary Search",
            "description": "Find target in sorted array.",
            "constraints": "1 <= n <= 1000",
            "examples": [{"input": "[1,3,5], 3", "output": "1", "explanation": "found at index 1"}],
            "hints": ["Use left/right pointers"],
            "solution": {"code": "...", "explanation": "...", "time_complexity": "O(log n)", "space_complexity": "O(1)"},
            "tags": ["binary-search"],
        }
        problem = ProblemGeneratorService._dict_to_problem(data, "dsa", "binary_search", "medium", ProblemSource.static)
        assert problem is not None
        assert problem.title == "Binary Search"
        assert problem.source == ProblemSource.static
        assert len(problem.examples) == 1
        assert problem.solution is not None
        assert problem.solution.time_complexity == "O(log n)"

    def test_missing_title_returns_none(self):
        assert ProblemGeneratorService._dict_to_problem(
            {"description": "desc"}, "dsa", "a", "easy", ProblemSource.static
        ) is None

    def test_missing_description_returns_none(self):
        assert ProblemGeneratorService._dict_to_problem(
            {"title": "Title"}, "dsa", "a", "easy", ProblemSource.static
        ) is None

    def test_no_solution_is_fine(self):
        data = {"title": "T", "description": "D"}
        problem = ProblemGeneratorService._dict_to_problem(data, "dsa", "a", "easy", ProblemSource.static)
        assert problem is not None
        assert problem.solution is None

    def test_examples_parsed(self):
        data = {
            "title": "T", "description": "D",
            "examples": [{"input": "x", "output": "y", "explanation": "z"}],
        }
        problem = ProblemGeneratorService._dict_to_problem(data, "dsa", "a", "easy", ProblemSource.static)
        assert len(problem.examples) == 1
        assert problem.examples[0].input == "x"


class TestGenerationValidation:
    """Generated problems must be self-verifying — bad solutions are rejected."""

    def test_unverifiable_solution_rejected(self):
        bad = _problem_json(solution={
            "code": "print('wrong answer')",
            "explanation": "", "time_complexity": "O(1)", "space_complexity": "O(1)",
        })
        svc = ProblemGeneratorService(MockLLMClient(response=bad))
        assert svc.generate_dsa("two_pointers", "medium") is None

    def test_function_style_examples_rejected(self):
        bad = _problem_json(examples=[
            {"input": "nums = [2, 7], target = 9", "output": "[0, 1]", "explanation": ""},
            {"input": "nums = [1, 3], target = 4", "output": "[0, 1]", "explanation": ""},
        ])
        svc = ProblemGeneratorService(MockLLMClient(response=bad))
        assert svc.generate_dsa("two_pointers", "medium") is None

    def test_missing_solution_rejected(self):
        bad = _problem_json(solution=None)
        svc = ProblemGeneratorService(MockLLMClient(response=bad))
        assert svc.generate_python_fundamental("OOP", "oop") is None

    def test_single_example_rejected(self):
        bad = _problem_json(examples=[{"input": "2 7\n9", "output": "0 1", "explanation": ""}])
        svc = ProblemGeneratorService(MockLLMClient(response=bad))
        assert svc.generate_dsa("two_pointers", "medium") is None

    def test_verified_problem_accepted(self):
        svc = ProblemGeneratorService(MockLLMClient(response=_problem_json()))
        problem = svc.generate_dsa("two_pointers", "medium")
        assert problem is not None
        assert ProblemGeneratorService.is_verified(problem)

    def test_list_generation_filters_unverified(self):
        good = json.loads(_problem_json())
        bad = json.loads(_problem_json(title="Broken", solution={
            "code": "print('nope')", "explanation": "",
            "time_complexity": "O(1)", "space_complexity": "O(1)",
        }))
        svc = ProblemGeneratorService(MockLLMClient(response=json.dumps([good, bad])))
        problems = svc.generate_from_jd("backend role", count=2)
        assert [p.title for p in problems] == ["Two Sum"]

    def test_validation_can_be_disabled(self):
        bad = _problem_json(solution={"code": "print('x')", "explanation": "",
                                      "time_complexity": "O(1)", "space_complexity": "O(1)"})
        svc = ProblemGeneratorService(MockLLMClient(response=bad), validate=False)
        assert svc.generate_dsa("two_pointers", "medium") is not None
