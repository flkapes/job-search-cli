"""Safe code execution in a subprocess sandbox with deterministic verification."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field

from codepractice.utils.languages import build_run_command


@dataclass
class RunResult:
    passed: bool
    stdout: str
    stderr: str
    error: str
    runtime_ms: float


@dataclass
class TestCaseResult:
    """Outcome of running code against one test case.

    ``comparable`` is True when the case produced a definite verdict:
    either the output could be checked against ``expected``, or execution
    failed outright. Function-style solutions that print nothing cannot be
    verified via stdout and are reported as not comparable rather than failed.
    """

    passed: bool
    comparable: bool
    expected: str = ""
    actual: str = ""
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    runtime_ms: float = 0.0


@dataclass
class VerificationSummary:
    """Aggregate of deterministic test-case results for one submission."""

    total: int = 0
    comparable: int = 0
    passed: int = 0
    failed: int = 0
    results: list[TestCaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.comparable == 0:
            return 0.0
        return self.passed / self.comparable

    @property
    def all_passed(self) -> bool:
        return self.comparable > 0 and self.failed == 0

    @property
    def fully_verified(self) -> bool:
        """Every test case produced a verdict and all of them passed."""
        return self.total > 0 and self.comparable == self.total and self.failed == 0

    @property
    def indeterminate(self) -> bool:
        return self.comparable == 0


def run_code(code: str, timeout: int = 10, stdin: str = "", language: str = "python") -> RunResult:
    """Execute code in a subprocess with timeout."""
    if not code.strip():
        return RunResult(passed=False, stdout="", stderr="", error="No code provided", runtime_ms=0)

    try:
        cmd, cleanup = build_run_command(code, language)
    except ValueError as e:
        return RunResult(passed=False, stdout="", stderr="", error=str(e), runtime_ms=0)

    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
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
    finally:
        cleanup()


def normalize_output(text: str) -> str:
    """Normalize program output for comparison: trailing whitespace and blank edges."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines)


def run_with_test_cases(
    code: str,
    test_cases: list[dict],
    timeout: int = 10,
    language: str = "python",
) -> list[TestCaseResult]:
    """Run code against test cases ({input, expected_output}) and verify output.

    A case passes when execution succeeds and, if an expected output is given,
    the program's stdout matches it (whitespace-normalized). Cases where
    verification is impossible (no expected output, or the solution prints
    nothing) are marked ``comparable=False`` so callers can treat them as
    indeterminate instead of failed.
    """
    results: list[TestCaseResult] = []
    for tc in test_cases:
        stdin = str(tc.get("input", "") or "")
        expected = str(tc.get("expected_output", tc.get("output", "")) or "")
        run = run_code(code, timeout=timeout, stdin=stdin, language=language)

        if not run.passed:
            # Crash / timeout / nonzero exit is a definite failure.
            results.append(TestCaseResult(
                passed=False, comparable=True, expected=expected,
                actual=run.stdout, stdout=run.stdout, stderr=run.stderr,
                error=run.error, runtime_ms=run.runtime_ms,
            ))
            continue

        actual = normalize_output(run.stdout)
        expected_norm = normalize_output(expected)

        if not expected_norm or not actual:
            # No expected output, or function-style code that prints nothing:
            # execution succeeded but correctness can't be verified via stdout.
            results.append(TestCaseResult(
                passed=True, comparable=False, expected=expected,
                actual=actual, stdout=run.stdout, stderr=run.stderr,
                runtime_ms=run.runtime_ms,
            ))
            continue

        results.append(TestCaseResult(
            passed=actual == expected_norm, comparable=True, expected=expected_norm,
            actual=actual, stdout=run.stdout, stderr=run.stderr,
            runtime_ms=run.runtime_ms,
        ))
    return results


def summarize_results(results: list[TestCaseResult]) -> VerificationSummary:
    comparable = [r for r in results if r.comparable]
    return VerificationSummary(
        total=len(results),
        comparable=len(comparable),
        passed=sum(1 for r in comparable if r.passed),
        failed=sum(1 for r in comparable if not r.passed),
        results=results,
    )


def clamp_score(score: float, passed: bool, summary: VerificationSummary | None) -> tuple[float, bool]:
    """Apply deterministic guardrails to an LLM-judged score.

    The LLM refines within the bounds the test results allow — it cannot pass
    code that fails its test cases, and fully verified code gets a floor.
    """
    if summary is None or summary.indeterminate:
        return score, passed

    if summary.failed > 0:
        if summary.passed == 0:
            score = min(score, 0.4)
        else:
            score = min(score, 0.65)
        return score, False

    if summary.fully_verified:
        score = max(score, 0.7)
        return score, True

    return score, passed
