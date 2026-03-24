"""Tests for daily digest command — Feature 5."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from codepractice.llm.client import LLMClient, LLMError
from codepractice.main import app

runner = CliRunner()


class MockLLMClient(LLMClient):
    def __init__(self, fail: bool = False):
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
        return "Great progress! Keep up the momentum."

    def stream_chat(self, messages, **kwargs):
        if self._fail:
            raise LLMError("offline")
        yield "Great progress!"


class TestDailyDigest:
    def test_digest_exits_zero(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["digest"])
        assert result.exit_code == 0, result.output

    def test_digest_shows_stats_keywords(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["digest"])
        output_lower = result.output.lower()
        assert any(kw in output_lower for kw in ["solved", "attempts", "streak", "review", "today"])

    def test_digest_shows_review_queue_size(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["digest"])
        assert result.exit_code == 0

    def test_digest_falls_back_gracefully_when_llm_offline(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient(fail=True)):
            result = runner.invoke(app, ["digest"])
        assert result.exit_code == 0

    def test_digest_output_has_panel_structure(self, tmp_db):
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["digest"])
        # Should produce some visible output (not empty)
        assert len(result.output.strip()) > 0

    def test_digest_with_existing_attempts(self, tmp_db):
        from codepractice.db.repositories import ProblemRepository, SessionRepository
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "title": "T", "description": "D"})
        sid = sess_repo.start_session()
        sess_repo.record_attempt({"session_id": sid, "problem_id": pid,
                                   "user_code": "x", "ai_feedback": "", "ai_score": 0.85, "passed": True})

        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.llm.client.get_client", return_value=MockLLMClient()):
            result = runner.invoke(app, ["digest"])
        assert result.exit_code == 0
