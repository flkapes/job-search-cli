"""Tests for ChatService using mock LLM client and tmp_db."""

from __future__ import annotations

from typing import Generator

from codepractice.db.repositories.chat_history import ChatHistoryRepository
from codepractice.llm.client import LLMClient, LLMError
from codepractice.llm.services.chat_service import ChatService


class MockLLMClient(LLMClient):
    def __init__(self, response: str = "AI reply", fail: bool = False):
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

    def stream_chat(self, messages, **kwargs) -> Generator[str, None, None]:
        if self._fail:
            raise LLMError("offline")
        yield from self._response.split()


class TestChatService:
    def _make_service(self, tmp_db, response="Hello!", fail=False, conv_id="default"):
        repo = ChatHistoryRepository(tmp_db)
        client = MockLLMClient(response=response, fail=fail)
        return ChatService(client, repo, conversation_id=conv_id), repo

    def test_stream_response_yields_tokens(self, tmp_db):
        svc, _ = self._make_service(tmp_db, response="Great work!")
        tokens = list(svc.stream_response("How am I doing?"))
        assert len(tokens) > 0
        assert "".join(tokens).strip() != ""

    def test_stream_response_saves_user_message(self, tmp_db):
        svc, repo = self._make_service(tmp_db)
        list(svc.stream_response("What is a decorator?"))
        history = repo.get_history()
        user_msgs = [m for m in history if m["role"] == "user"]
        assert any("decorator" in m["content"] for m in user_msgs)

    def test_stream_response_saves_assistant_reply(self, tmp_db):
        svc, repo = self._make_service(tmp_db, response="A decorator wraps a function.")
        list(svc.stream_response("Explain decorators"))
        history = repo.get_history()
        assistant_msgs = [m for m in history if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert "decorator" in assistant_msgs[0]["content"].lower()

    def test_stream_response_llm_failure_yields_error(self, tmp_db):
        svc, _ = self._make_service(tmp_db, fail=True)
        tokens = list(svc.stream_response("hi"))
        full = "".join(tokens)
        assert "unavailable" in full.lower() or "llm" in full.lower()

    def test_get_history_empty(self, tmp_db):
        svc, _ = self._make_service(tmp_db)
        assert svc.get_history() == []

    def test_get_history_after_chat(self, tmp_db):
        svc, _ = self._make_service(tmp_db)
        list(svc.stream_response("hello"))
        history = svc.get_history()
        assert len(history) == 2  # user + assistant

    def test_clear_removes_history(self, tmp_db):
        svc, _ = self._make_service(tmp_db)
        list(svc.stream_response("hello"))
        svc.clear()
        assert svc.get_history() == []

    def test_separate_conversations_isolated(self, tmp_db):
        repo = ChatHistoryRepository(tmp_db)
        client = MockLLMClient(response="hi")
        svc_a = ChatService(client, repo, conversation_id="a")
        svc_b = ChatService(client, repo, conversation_id="b")
        list(svc_a.stream_response("message in A"))
        assert svc_b.get_history() == []

    def test_analyze_resume_returns_dict(self, tmp_db):
        response = '{"skills": ["Python"], "languages": ["Python"], "years_experience": 3}'
        svc, _ = self._make_service(tmp_db, response=response)
        result = svc.analyze_resume("5 years Python developer...")
        assert isinstance(result, dict)

    def test_analyze_resume_llm_failure_returns_empty(self, tmp_db):
        svc, _ = self._make_service(tmp_db, fail=True)
        result = svc.analyze_resume("resume text")
        assert result == {}

    def test_stream_with_active_plan(self, tmp_db):
        from codepractice.core.models import DayPlan, LearningPlan
        plan = LearningPlan(
            title="Python Plan",
            current_day=2,
            daily_schedule=[DayPlan(day_number=2, theme="Graphs")],
        )
        svc, _ = self._make_service(tmp_db)
        tokens = list(svc.stream_response("what should I focus on?", active_plan=plan))
        assert len(tokens) > 0
