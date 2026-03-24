"""Text utilities: markdown rendering, formatting helpers."""

from __future__ import annotations

import re


def truncate(text: str, max_len: int = 80, suffix: str = "…") -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def score_to_color(score: float) -> str:
    """Map a 0-1 score to a rich color name."""
    if score >= 0.85:
        return "green"
    if score >= 0.6:
        return "yellow"
    return "red"


def score_to_emoji(score: float) -> str:
    if score >= 0.85:
        return "✓"
    if score >= 0.6:
        return "~"
    return "✗"


def difficulty_color(difficulty: str) -> str:
    return {"easy": "green", "medium": "yellow", "hard": "red"}.get(difficulty.lower(), "white")


def difficulty_badge(difficulty: str) -> str:
    colors = {"easy": "green", "medium": "yellow", "hard": "red"}
    color = colors.get(difficulty.lower(), "white")
    return f"[{color}]{difficulty.upper()}[/{color}]"


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def strip_markdown_code_fences(text: str) -> str:
    """Remove ```python ... ``` fences from LLM output."""
    return re.sub(r"```(?:\w+)?\n?([\s\S]+?)```", r"\1", text).strip()


def wrap_code_block(code: str, language: str = "python") -> str:
    """Wrap code in markdown fences."""
    return f"```{language}\n{code}\n```"


def build_progress_bar(current: int, total: int, width: int = 20, filled: str = "█", empty: str = "░") -> str:
    if total == 0:
        return empty * width
    pct = min(current / total, 1.0)
    filled_count = int(pct * width)
    return filled * filled_count + empty * (width - filled_count)
