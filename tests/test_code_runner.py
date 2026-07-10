"""Tests for the subprocess code execution sandbox."""

from __future__ import annotations

from codepractice.utils.code_runner import (
    RunResult,
    VerificationSummary,
    clamp_score,
    normalize_output,
    run_code,
    run_with_test_cases,
    summarize_results,
)


class TestRunCode:
    def test_simple_print(self):
        result = run_code("print('hello')")
        assert result.passed is True
        assert "hello" in result.stdout
        assert result.error == ""

    def test_empty_code_fails(self):
        result = run_code("")
        assert result.passed is False
        assert result.error != ""

    def test_whitespace_only_fails(self):
        result = run_code("   \n\t  ")
        assert result.passed is False

    def test_syntax_error_captured(self):
        result = run_code("def broken(: pass")
        assert result.passed is False
        assert len(result.stderr) > 0 or result.error

    def test_runtime_error_captured(self):
        result = run_code("x = 1 / 0")
        assert result.passed is False
        assert "ZeroDivisionError" in result.stderr or "ZeroDivisionError" in result.error

    def test_exit_code_nonzero_fails(self):
        result = run_code("import sys; sys.exit(1)")
        assert result.passed is False
        assert "Exit code 1" in result.error

    def test_stdout_captured(self):
        result = run_code("for i in range(3): print(i)")
        assert result.passed is True
        assert "0" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout

    def test_runtime_ms_positive(self):
        result = run_code("x = 1 + 1")
        assert result.runtime_ms >= 0

    def test_timeout_enforcement(self):
        # Killed either by the wall-clock timeout or by RLIMIT_CPU (SIGXCPU) —
        # whichever fires first; both are acceptable terminations.
        result = run_code("while True: pass", timeout=1)
        assert result.passed is False
        assert "Timed out" in result.error or "Exit code" in result.error

    def test_multiline_code(self):
        code = """
def add(a, b):
    return a + b

print(add(3, 4))
"""
        result = run_code(code)
        assert result.passed is True
        assert "7" in result.stdout

    def test_stdout_truncated_at_2000(self):
        code = "print('x' * 5000)"
        result = run_code(code)
        assert len(result.stdout) <= 2000

    def test_runresult_dataclass_fields(self):
        result = RunResult(passed=True, stdout="ok", stderr="", error="", runtime_ms=10.5)
        assert result.passed is True
        assert result.stdout == "ok"
        assert result.runtime_ms == 10.5


class TestRunWithTestCases:
    def test_matching_output_passes(self):
        code = "print('hello')"
        results = run_with_test_cases(code, [
            {"input": "", "expected_output": "hello"},
            {"input": "", "expected_output": "hello"},
        ])
        assert len(results) == 2
        assert all(r.passed and r.comparable for r in results)

    def test_wrong_output_fails(self):
        code = "print('goodbye')"
        results = run_with_test_cases(code, [{"input": "", "expected_output": "hello"}])
        assert results[0].passed is False
        assert results[0].comparable is True
        assert results[0].expected == "hello"
        assert results[0].actual == "goodbye"

    def test_exit_zero_alone_is_not_a_pass(self):
        """Code that runs cleanly but prints the wrong answer must fail."""
        code = "print(1 + 1)"
        results = run_with_test_cases(code, [{"input": "", "expected_output": "3"}])
        assert results[0].passed is False

    def test_crash_is_definite_failure(self):
        code = "raise ValueError('bad')"
        results = run_with_test_cases(code, [{"input": "", "expected_output": ""}])
        assert results[0].passed is False
        assert results[0].comparable is True

    def test_stdin_is_fed_to_program(self):
        code = "print(int(input()) * 2)"
        results = run_with_test_cases(code, [{"input": "21", "expected_output": "42"}])
        assert results[0].passed is True

    def test_function_style_code_is_indeterminate(self):
        """Definitions with no prints can't be verified — not failed."""
        code = "def add(a, b):\n    return a + b"
        results = run_with_test_cases(code, [{"input": "", "expected_output": "7"}])
        assert results[0].comparable is False
        assert results[0].passed is True

    def test_no_expected_output_is_indeterminate(self):
        code = "print('anything')"
        results = run_with_test_cases(code, [{"input": "", "expected_output": ""}])
        assert results[0].comparable is False

    def test_output_key_fallback(self):
        """Problem examples use 'output' rather than 'expected_output'."""
        code = "print('ok')"
        results = run_with_test_cases(code, [{"input": "", "output": "ok"}])
        assert results[0].passed is True
        assert results[0].comparable is True

    def test_whitespace_normalized_comparison(self):
        code = "print('a  ')\nprint('b')"
        results = run_with_test_cases(code, [{"input": "", "expected_output": "a\nb\n"}])
        assert results[0].passed is True

    def test_empty_test_cases_returns_empty(self):
        results = run_with_test_cases("x = 1", [])
        assert results == []


class TestNormalizeOutput:
    def test_strips_trailing_whitespace_per_line(self):
        assert normalize_output("a  \nb\t\n") == "a\nb"

    def test_strips_surrounding_blank_lines(self):
        assert normalize_output("\n\nhello\n\n") == "hello"


class TestSummarizeResults:
    def test_counts(self):
        code = "print('x')"
        results = run_with_test_cases(code, [
            {"input": "", "expected_output": "x"},
            {"input": "", "expected_output": "y"},
            {"input": "", "expected_output": ""},
        ])
        summary = summarize_results(results)
        assert summary.total == 3
        assert summary.comparable == 2
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.pass_rate == 0.5
        assert summary.all_passed is False

    def test_fully_verified(self):
        code = "print('x')"
        results = run_with_test_cases(code, [{"input": "", "expected_output": "x"}])
        summary = summarize_results(results)
        assert summary.fully_verified is True

    def test_indeterminate(self):
        summary = summarize_results([])
        assert summary.indeterminate is True


class TestClampScore:
    def _summary(self, total, comparable, passed):
        return VerificationSummary(
            total=total, comparable=comparable,
            passed=passed, failed=comparable - passed,
        )

    def test_no_summary_leaves_score_alone(self):
        assert clamp_score(0.9, True, None) == (0.9, True)

    def test_indeterminate_leaves_score_alone(self):
        assert clamp_score(0.9, True, self._summary(2, 0, 0)) == (0.9, True)

    def test_all_failures_caps_hard(self):
        score, passed = clamp_score(0.95, True, self._summary(2, 2, 0))
        assert score == 0.4
        assert passed is False

    def test_partial_failures_cap(self):
        score, passed = clamp_score(0.9, True, self._summary(3, 3, 2))
        assert score == 0.65
        assert passed is False

    def test_llm_cannot_pass_failing_code(self):
        _, passed = clamp_score(1.0, True, self._summary(1, 1, 0))
        assert passed is False

    def test_fully_verified_floors_harsh_llm_score(self):
        # LLM passed it but scored low — tests passing raise the floor.
        score, passed = clamp_score(0.55, True, self._summary(2, 2, 2))
        assert score == 0.7
        assert passed is True

    def test_fully_verified_overrules_borderline_llm_fail(self):
        # LLM failed it with a middling score — deterministic pass wins.
        score, passed = clamp_score(0.55, False, self._summary(2, 2, 2))
        assert score == 0.7
        assert passed is True

    def test_emphatic_llm_fail_survives_verification(self):
        # Examples pass but the LLM emphatically failed it (e.g. hard-coded
        # outputs) — the smoke test must not overrule that verdict.
        score, passed = clamp_score(0.2, False, self._summary(2, 2, 2))
        assert score == 0.55
        assert passed is False

    def test_partial_verification_no_floor(self):
        score, passed = clamp_score(0.5, False, self._summary(3, 2, 2))
        assert score == 0.5
        assert passed is False

    def test_low_score_untouched_when_failing(self):
        score, passed = clamp_score(0.2, False, self._summary(1, 1, 0))
        assert score == 0.2
        assert passed is False
