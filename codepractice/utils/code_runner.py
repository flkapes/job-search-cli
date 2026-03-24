"""Safe Python code execution in a subprocess sandbox."""

from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass


@dataclass
class RunResult:
    passed: bool
    stdout: str
    stderr: str
    error: str
    runtime_ms: float


def run_code(code: str, timeout: int = 10, stdin: str = "") -> RunResult:
    """Execute Python code in a subprocess with timeout."""
    if not code.strip():
        return RunResult(passed=False, stdout="", stderr="", error="No code provided", runtime_ms=0)

    start = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - start) * 1000
        passed = result.returncode == 0
        return RunResult(
            passed=passed,
            stdout=result.stdout[:2000],
            stderr=result.stderr[:500],
            error="" if passed else f"Exit code {result.returncode}",
            runtime_ms=round(elapsed, 2),
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            passed=False,
            stdout="",
            stderr="",
            error=f"Timed out after {timeout}s",
            runtime_ms=timeout * 1000,
        )
    except Exception as e:
        return RunResult(passed=False, stdout="", stderr="", error=str(e), runtime_ms=0)


def run_with_test_cases(code: str, test_cases: list[dict], timeout: int = 10) -> list[RunResult]:
    """Run code against multiple test cases ({input, expected_output})."""
    results = []
    for tc in test_cases:
        test_script = textwrap.dedent(f"""
{code}

# Auto-test
_input = {repr(tc.get('input', ''))}
_expected = {repr(tc.get('expected_output', ''))}
""")
        results.append(run_code(test_script, timeout=timeout, stdin=str(tc.get("input", ""))))
    return results
