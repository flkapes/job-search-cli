"""Tests for text utility helpers."""

from __future__ import annotations

from codepractice.utils.text_utils import (
    build_progress_bar,
    difficulty_badge,
    difficulty_color,
    format_duration,
    score_to_color,
    score_to_emoji,
    strip_markdown_code_fences,
    truncate,
    wrap_code_block,
)


class TestTruncate:
    def test_short_string_unchanged(self):
        assert truncate("hello", 80) == "hello"

    def test_exact_length_unchanged(self):
        s = "x" * 80
        assert truncate(s, 80) == s

    def test_long_string_truncated(self):
        s = "x" * 100
        result = truncate(s, 80)
        assert len(result) == 80
        assert result.endswith("…")

    def test_custom_suffix(self):
        result = truncate("hello world", 8, suffix="...")
        assert result.endswith("...")
        assert len(result) == 8

    def test_empty_string(self):
        assert truncate("", 10) == ""


class TestScoreToColor:
    def test_high_score_green(self):
        assert score_to_color(0.85) == "green"
        assert score_to_color(1.0) == "green"

    def test_mid_score_yellow(self):
        assert score_to_color(0.6) == "yellow"
        assert score_to_color(0.84) == "yellow"

    def test_low_score_red(self):
        assert score_to_color(0.0) == "red"
        assert score_to_color(0.59) == "red"

    def test_boundary_085(self):
        assert score_to_color(0.85) == "green"

    def test_boundary_06(self):
        assert score_to_color(0.6) == "yellow"


class TestScoreToEmoji:
    def test_high_score_checkmark(self):
        assert score_to_emoji(0.9) == "✓"
        assert score_to_emoji(0.85) == "✓"

    def test_mid_score_tilde(self):
        assert score_to_emoji(0.7) == "~"

    def test_low_score_cross(self):
        assert score_to_emoji(0.3) == "✗"
        assert score_to_emoji(0.0) == "✗"


class TestDifficultyColor:
    def test_easy_green(self):
        assert difficulty_color("easy") == "green"
        assert difficulty_color("Easy") == "green"
        assert difficulty_color("EASY") == "green"

    def test_medium_yellow(self):
        assert difficulty_color("medium") == "yellow"

    def test_hard_red(self):
        assert difficulty_color("hard") == "red"

    def test_unknown_white(self):
        assert difficulty_color("unknown") == "white"


class TestDifficultyBadge:
    def test_easy_badge(self):
        badge = difficulty_badge("easy")
        assert "EASY" in badge
        assert "green" in badge

    def test_medium_badge(self):
        badge = difficulty_badge("medium")
        assert "MEDIUM" in badge
        assert "yellow" in badge

    def test_hard_badge(self):
        badge = difficulty_badge("hard")
        assert "HARD" in badge
        assert "red" in badge


class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(45) == "45s"
        assert format_duration(0) == "0s"
        assert format_duration(59) == "59s"

    def test_minutes_and_seconds(self):
        assert format_duration(90) == "1m 30s"
        assert format_duration(60) == "1m 0s"

    def test_hours_and_minutes(self):
        assert format_duration(3600) == "1h 0m"
        assert format_duration(3661) == "1h 1m"
        assert format_duration(7200) == "2h 0m"


class TestStripMarkdownCodeFences:
    def test_strips_python_fence(self):
        code = "```python\ndef hello():\n    pass\n```"
        result = strip_markdown_code_fences(code)
        assert "```" not in result
        assert "def hello():" in result

    def test_strips_plain_fence(self):
        result = strip_markdown_code_fences("```\nsome code\n```")
        assert "```" not in result
        assert "some code" in result

    def test_no_fences_unchanged(self):
        text = "just some text"
        assert strip_markdown_code_fences(text) == text

    def test_strips_multiple_fences(self):
        code = "```python\nx = 1\n```\n\n```python\ny = 2\n```"
        result = strip_markdown_code_fences(code)
        assert "```" not in result


class TestWrapCodeBlock:
    def test_wraps_python_by_default(self):
        result = wrap_code_block("x = 1")
        assert result.startswith("```python")
        assert "x = 1" in result
        assert result.endswith("```")

    def test_custom_language(self):
        result = wrap_code_block("fn main() {}", language="rust")
        assert "```rust" in result


class TestBuildProgressBar:
    def test_full_progress(self):
        bar = build_progress_bar(10, 10, width=10)
        assert bar == "█" * 10

    def test_zero_progress(self):
        bar = build_progress_bar(0, 10, width=10)
        assert bar == "░" * 10

    def test_half_progress(self):
        bar = build_progress_bar(5, 10, width=10)
        assert bar.count("█") == 5
        assert bar.count("░") == 5

    def test_zero_total_returns_empty(self):
        bar = build_progress_bar(0, 0, width=10)
        assert bar == "░" * 10

    def test_clamps_at_100_pct(self):
        bar = build_progress_bar(20, 10, width=10)
        assert bar == "█" * 10

    def test_custom_chars(self):
        bar = build_progress_bar(1, 2, width=4, filled="#", empty="-")
        assert "#" in bar
        assert "-" in bar
