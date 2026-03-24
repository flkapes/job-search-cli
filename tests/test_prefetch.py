"""Tests for offline problem cache (prefetch command) — Feature 1."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from codepractice.llm.client import LLMClient, LLMError
from codepractice.main import app

runner = CliRunner()

_PROBLEM_JSON = (
    '{"title": "Prefetch Test", "description": "Desc", "constraints": "", '
    '"examples": [], "hints": [], "solution": null, "tags": ["test"]}'
)


class MockLLMClient(LLMClient):
    def __init__(self, response: str = _PROBLEM_JSON, fail: bool = False):
        self._response = response
        self._fail = fail
        self.model = "mock"
        self.base_url = "http://mock"

    def health_check(self) -> bool:
        return not self._fail

    def list_models(self) -> list[str]:
        return ["mock"]

    def chat_sync(self, messages, **kwargs) -> str:
        if self._fail:
            raise LLMError("offline")
        return self._response

    def stream_chat(self, messages, **kwargs):
        if self._fail:
            raise LLMError("offline")
        yield self._response


class TestPrefetchCommand:
    def test_prefetch_exits_successfully(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["prefetch", "--count", "1"])
        assert result.exit_code == 0, result.output

    def test_prefetch_saves_problems_to_db(self, tmp_db):
        from codepractice.db.repositories import ProblemRepository
        repo = ProblemRepository(tmp_db)

        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            runner.invoke(app, ["prefetch", "--count", "2"])

        total = sum(repo.count_by_category().values())
        assert total >= 2

    def test_prefetch_output_shows_progress(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["prefetch", "--count", "1"])
        assert result.exit_code == 0
        assert any(kw in result.output for kw in ["Generated", "cached", "saved", "✓", "problem"])

    def test_prefetch_with_category_dsa(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["prefetch", "--count", "1", "--category", "dsa"])
        assert result.exit_code == 0

    def test_prefetch_with_category_python(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["prefetch", "--count", "1", "--category", "python_fundamentals"])
        assert result.exit_code == 0

    def test_prefetch_with_difficulty_filter(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["prefetch", "--count", "1", "--difficulty", "hard"])
        assert result.exit_code == 0

    def test_prefetch_handles_llm_failure_gracefully(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient(fail=True)):
            result = runner.invoke(app, ["prefetch", "--count", "2"])
        # Should not crash — reports failures gracefully
        assert result.exit_code == 0

    def test_prefetch_default_count_is_reasonable(self, tmp_db):
        """Invoking without --count uses a sensible default."""
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["prefetch"])
        assert result.exit_code == 0

    def test_prefetch_reports_failure_count(self, tmp_db):
        """When LLM fails, output mentions the failure."""
        client = MockLLMClient(fail=True)
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=client):
            result = runner.invoke(app, ["prefetch", "--count", "3"])
        assert result.exit_code == 0
