"""Tests for code diff view (extract optimized solution) — Feature 7."""

from __future__ import annotations

from codepractice.utils.text_utils import extract_optimized_solution, should_show_diff


class TestExtractOptimizedSolution:
    def test_extracts_from_json_field(self):
        raw = '{"score": 0.7, "optimized_solution": "def fast(): return 42"}'
        result = extract_optimized_solution(raw)
        assert result == "def fast(): return 42"

    def test_returns_none_when_field_absent(self):
        raw = '{"score": 0.9, "passed": true}'
        assert extract_optimized_solution(raw) is None

    def test_returns_none_for_plain_text(self):
        assert extract_optimized_solution("Good solution!") is None

    def test_returns_none_for_empty_string(self):
        assert extract_optimized_solution("") is None

    def test_extracts_multiline_solution(self):
        raw = '{"score": 0.6, "optimized_solution": "def solve(n):\\n    return n * 2"}'
        result = extract_optimized_solution(raw)
        assert result is not None
        assert "def solve" in result

    def test_handles_embedded_in_prose(self):
        raw = 'Good attempt!\n{"score": 0.7, "optimized_solution": "def better(): return 1"}'
        result = extract_optimized_solution(raw)
        assert result is not None
        assert "better" in result

    def test_returns_none_for_malformed_json(self):
        assert extract_optimized_solution("{not valid json}") is None

    def test_strips_code_fence_if_present(self):
        raw = '{"score": 0.5, "optimized_solution": "```python\\ndef x(): pass\\n```"}'
        result = extract_optimized_solution(raw)
        assert result is not None
        assert "def x" in result

    def test_empty_optimized_solution_returns_none(self):
        raw = '{"score": 0.7, "optimized_solution": ""}'
        assert extract_optimized_solution(raw) is None

    def test_whitespace_only_solution_returns_none(self):
        raw = '{"score": 0.7, "optimized_solution": "   "}'
        assert extract_optimized_solution(raw) is None


class TestShouldShowDiff:
    def test_shows_for_low_score(self):
        assert should_show_diff(0.5) is True
        assert should_show_diff(0.0) is True

    def test_shows_at_boundary(self):
        assert should_show_diff(0.89) is True

    def test_hides_at_09(self):
        assert should_show_diff(0.9) is False

    def test_hides_for_perfect_score(self):
        assert should_show_diff(1.0) is False

    def test_hides_above_09(self):
        assert should_show_diff(0.95) is False

    def test_shows_at_exactly_089(self):
        assert should_show_diff(0.89) is True
