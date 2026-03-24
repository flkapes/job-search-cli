"""Tests for the subprocess code execution sandbox."""

from __future__ import annotations

from codepractice.utils.code_runner import RunResult, run_code, run_with_test_cases


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
        result = run_code("while True: pass", timeout=1)
        assert result.passed is False
        assert "Timed out" in result.error

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
    def test_single_test_case_pass(self):
        code = "x = 1"  # code that runs without error
        results = run_with_test_cases(code, [{"input": "", "expected_output": ""}])
        assert len(results) == 1
        assert results[0].passed is True

    def test_multiple_test_cases(self):
        code = "print('hello')"
        results = run_with_test_cases(code, [
            {"input": "", "expected_output": "hello"},
            {"input": "", "expected_output": "hello"},
        ])
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_failing_test_case(self):
        code = "raise ValueError('bad')"
        results = run_with_test_cases(code, [{"input": "", "expected_output": ""}])
        assert len(results) == 1
        assert results[0].passed is False

    def test_empty_test_cases_returns_empty(self):
        results = run_with_test_cases("x = 1", [])
        assert results == []
