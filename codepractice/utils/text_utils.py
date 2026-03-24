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


def extract_optimized_solution(raw: str) -> str | None:
    """
    Extract the 'optimized_solution' field from AI feedback JSON.
    Returns None if not present, empty, or unparseable.
    """
    if not raw:
        return None
    import json as _json
    # Try to find JSON in the text
    text = raw.strip()
    # Look for embedded JSON object
    for start in (text.find("{"), 0):
        if start < 0:
            break
        brace_start = text.find("{", start)
        if brace_start < 0:
            break
        # Find matching close brace
        depth = 0
        for i, ch in enumerate(text[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = _json.loads(text[brace_start : i + 1])
                        if isinstance(data, dict):
                            solution = data.get("optimized_solution", "")
                            if solution and solution.strip():
                                return strip_markdown_code_fences(solution)
                    except (_json.JSONDecodeError, Exception):
                        pass
                    break
        break
    return None


def should_show_diff(score: float) -> bool:
    """Return True if a code diff should be shown (score below near-perfect threshold)."""
    return score < 0.9


def build_progress_bar(current: int, total: int, width: int = 20, filled: str = "█", empty: str = "░") -> str:
    if total == 0:
        return empty * width
    pct = min(current / total, 1.0)
    filled_count = int(pct * width)
    return filled * filled_count + empty * (width - filled_count)
