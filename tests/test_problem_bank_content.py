"""Quality guard for the bundled problem bank.

Every bundled problem must be well-formed, cover the advertised tracks, and —
critically — carry a reference solution that actually produces the expected
output for every example, so the verified-test-cases feature works on all
bundled content and offline scoring is meaningful.
"""

from __future__ import annotations

import collections

import pytest

from codepractice.config import DSA_PATTERNS, PYTHON_TOPICS
from codepractice.core.models import Problem
from codepractice.core.problem_bank import load_all_problems
from codepractice.utils.code_runner import run_with_test_cases

PROBLEMS = load_all_problems()
DIFFICULTIES = {"easy", "medium", "hard"}


class TestBankShape:
    def test_at_least_fifty_problems(self):
        assert len(PROBLEMS) >= 50

    def test_titles_unique(self):
        titles = [p["title"] for p in PROBLEMS]
        dupes = [t for t, n in collections.Counter(titles).items() if n > 1]
        assert not dupes, f"Duplicate titles: {dupes}"

    def test_every_problem_parses_as_model(self):
        for p in PROBLEMS:
            problem = Problem.from_db({**p, "id": 1})
            assert problem.title and problem.description
            assert problem.difficulty.value in DIFFICULTIES

    def test_every_problem_has_hints_and_solution(self):
        for p in PROBLEMS:
            assert p.get("hints"), p["title"]
            assert (p.get("solution") or {}).get("code"), p["title"]

    def test_every_problem_has_verifiable_examples(self):
        for p in PROBLEMS:
            examples = p.get("examples", [])
            comparable = [e for e in examples if e.get("output")]
            assert len(comparable) >= 2, f"{p['title']} needs >= 2 checked examples"


class TestTrackCoverage:
    def test_every_dsa_pattern_has_all_difficulties(self):
        coverage = collections.defaultdict(set)
        for p in PROBLEMS:
            if p["category"] == "dsa":
                coverage[p["subcategory"]].add(p["difficulty"])
        for pattern in DSA_PATTERNS:
            assert coverage[pattern["id"]] == DIFFICULTIES, (
                f"Pattern '{pattern['id']}' missing difficulties: "
                f"{DIFFICULTIES - coverage[pattern['id']]}"
            )

    def test_every_python_topic_has_three_problems(self):
        counts = collections.Counter(
            p["subcategory"] for p in PROBLEMS if p["category"] == "python_fundamentals"
        )
        for topic in PYTHON_TOPICS:
            assert counts[topic["id"]] >= 3, f"Topic '{topic['id']}' has {counts[topic['id']]}"

    def test_practical_category_present(self):
        assert sum(1 for p in PROBLEMS if p["category"] == "practical") >= 5


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda p: p["title"])
def test_reference_solution_passes_its_own_examples(problem):
    cases = [
        {"input": e.get("input", ""), "expected_output": e["output"]}
        for e in problem["examples"]
        if e.get("output")
    ]
    results = run_with_test_cases(problem["solution"]["code"], cases, timeout=20)
    for i, result in enumerate(results):
        assert result.comparable, f"example {i + 1} not verifiable"
        assert result.passed, (
            f"example {i + 1}: expected {result.expected!r}, "
            f"got {result.actual!r} ({result.error} {result.stderr[:200]})"
        )
