"""Answer evaluation prompt templates."""

from __future__ import annotations

from codepractice.core.models import Problem
from codepractice.llm.prompts.base import system_message, user_message


def evaluate_prompt(
    problem: Problem,
    user_code: str,
    user_explanation: str,
    test_results: str = "",
) -> list[dict]:
    examples_str = "\n".join(
        f"  Input: {e.input}\n  Output: {e.output}"
        for e in problem.examples[:3]
    )

    return [
        system_message(
            """When evaluating code, stream your response in this order:
1. Quick verdict: ✓ Correct / ~ Partial / ✗ Incorrect
2. Correctness analysis (does it handle all cases?)
3. Time/space complexity breakdown
4. Style and Pythonic quality notes
5. Specific improvements with short code examples
6. On the LAST LINE output ONLY this JSON: {"score": 0.85, "passed": true}
   (score 0.0-1.0, passed = score >= 0.7)"""
        ),
        user_message(
            f"""Evaluate this solution:

**Problem:** {problem.title}
{problem.description[:800]}

**Examples:**
{examples_str}

**User's Code:**
```python
{user_code}
```

**User's Explanation:** {user_explanation or '(none provided)'}

{'**Test Results:** ' + test_results if test_results else ''}

Evaluate thoroughly. Be encouraging but honest."""
        ),
    ]


def quick_check_prompt(problem: Problem, user_code: str) -> list[dict]:
    """Faster evaluation that returns just a score JSON."""
    return [
        system_message(),
        user_message(
            f"""Quickly evaluate this code for the problem "{problem.title}".
Code:
```python
{user_code}
```
Respond with ONLY: {{"score": 0.0-1.0, "passed": true/false, "one_line_feedback": "string"}}"""
        ),
    ]
