"""Tests for multi-language practice support."""

from __future__ import annotations

import shutil

import pytest

from codepractice.db.repositories import GamificationRepository, ProblemRepository, SessionRepository
from codepractice.utils.code_runner import run_code, run_with_test_cases
from codepractice.utils.languages import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    available_languages,
    build_run_command,
    get_language,
    is_language_available,
)

has_node = shutil.which("node") is not None
has_go = shutil.which("go") is not None


class TestRegistry:
    def test_python_always_available(self):
        assert is_language_available("python") is True
        assert DEFAULT_LANGUAGE == "python"

    def test_three_languages_defined(self):
        assert set(LANGUAGES) == {"python", "javascript", "go"}

    def test_get_language_falls_back_to_python(self):
        assert get_language("cobol").id == "python"

    def test_editor_metadata(self):
        assert get_language("javascript").file_name == "solution.js"
        assert get_language("go").editor_language == "go"

    def test_available_languages_includes_python(self):
        ids = [s.id for s in available_languages()]
        assert "python" in ids

    def test_unknown_language_command_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            build_run_command("x", "cobol")

    def test_unavailable_toolchain_raises(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda _: None)
        with pytest.raises(ValueError, match="Node"):
            build_run_command("1", "javascript")


class TestPythonRunner:
    def test_default_language_is_python(self):
        result = run_code("print('py')")
        assert result.passed and "py" in result.stdout

    def test_unknown_language_returns_error_result(self):
        result = run_code("print(1)", language="cobol")
        assert result.passed is False
        assert "Unsupported" in result.error


@pytest.mark.skipif(not has_node, reason="node not installed")
class TestJavaScriptRunner:
    def test_hello(self):
        result = run_code("console.log('hello js')", language="javascript")
        assert result.passed is True
        assert "hello js" in result.stdout

    def test_verification(self):
        results = run_with_test_cases(
            "console.log(21 * 2)", [{"input": "", "expected_output": "42"}],
            language="javascript",
        )
        assert results[0].passed is True

    def test_wrong_output_fails(self):
        results = run_with_test_cases(
            "console.log('x')", [{"input": "", "expected_output": "y"}],
            language="javascript",
        )
        assert results[0].passed is False

    def test_syntax_error_fails(self):
        result = run_code("const = broken", language="javascript")
        assert result.passed is False


@pytest.mark.skipif(not has_go, reason="go not installed")
class TestGoRunner:
    def test_hello(self):
        code = 'package main\nimport "fmt"\nfunc main() { fmt.Println("hello go") }'
        result = run_code(code, language="go", timeout=60)
        assert result.passed is True
        assert "hello go" in result.stdout


class TestLanguagePersistence:
    def _attempt(self, tmp_db, language, passed=True):
        problems = ProblemRepository(tmp_db)
        sessions = SessionRepository(tmp_db)
        pid = problems.create({"category": "dsa", "title": "T", "description": "d"})
        sid = sessions.start_session("free")
        aid = sessions.record_attempt({
            "session_id": sid, "problem_id": pid, "ai_score": 0.9,
            "passed": passed, "language": language,
        })
        return sessions, aid

    def test_language_stored_on_attempt(self, tmp_db):
        sessions, aid = self._attempt(tmp_db, "javascript")
        assert sessions.get_attempt_by_id(aid)["language"] == "javascript"

    def test_language_defaults_to_python(self, tmp_db):
        problems = ProblemRepository(tmp_db)
        sessions = SessionRepository(tmp_db)
        pid = problems.create({"category": "dsa", "title": "T", "description": "d"})
        sid = sessions.start_session("free")
        aid = sessions.record_attempt({"session_id": sid, "problem_id": pid})
        assert sessions.get_attempt_by_id(aid)["language"] == "python"

    def test_polyglot_count(self, tmp_db):
        gam = GamificationRepository(tmp_db)
        self._attempt(tmp_db, "python")
        assert gam.languages_solved_count() == 1
        self._attempt(tmp_db, "javascript")
        assert gam.languages_solved_count() == 2
        self._attempt(tmp_db, "go", passed=False)  # failed attempts don't count
        assert gam.languages_solved_count() == 2


class TestEditorIntegration:
    def test_code_editor_has_language_api(self):
        from codepractice.tui.widgets.code_editor import CodeEditor
        editor = CodeEditor()
        assert editor.language == "python"

    def test_evaluator_prompt_mentions_language(self):
        from codepractice.core.models import Problem
        from codepractice.llm.prompts.evaluator import evaluate_prompt
        messages = evaluate_prompt(Problem(title="T", description="d"), "code", "", language="go")
        text = "\n".join(m["content"] for m in messages)
        assert "```go" in text
        assert "written in go" in text
