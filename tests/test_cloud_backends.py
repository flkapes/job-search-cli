"""Tests for the Anthropic and OpenAI-compatible cloud backends."""

from __future__ import annotations

from codepractice.llm.client import (
    AnthropicClient,
    LMStudioClient,
    OllamaClient,
    OpenAICompatClient,
    get_client,
)


class TestFactory:
    def test_default_is_ollama(self):
        assert isinstance(get_client(), OllamaClient)

    def test_anthropic_backend(self):
        client = get_client(backend="anthropic", model="claude-opus-4-8")
        assert isinstance(client, AnthropicClient)
        assert client.model == "claude-opus-4-8"

    def test_openai_backend(self):
        client = get_client(backend="openai", model="gpt-4o-mini")
        assert isinstance(client, OpenAICompatClient)
        assert client.model == "gpt-4o-mini"
        assert client.base_url == "https://api.openai.com/v1"

    def test_openai_custom_base_url(self):
        client = get_client(backend="openai", base_url="https://api.example.com/v1/")
        assert client.base_url == "https://api.example.com/v1"

    def test_lmstudio_still_works(self):
        assert isinstance(get_client(backend="lmstudio"), LMStudioClient)


class TestAnthropicClient:
    def test_split_system_extracts_system_messages(self):
        system, rest = AnthropicClient.split_system([
            {"role": "system", "content": "You are a coach."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Evaluate my code"},
        ])
        assert system == "You are a coach."
        assert len(rest) == 3
        assert all(m["role"] != "system" for m in rest)

    def test_split_system_joins_multiple(self):
        system, rest = AnthropicClient.split_system([
            {"role": "system", "content": "A"},
            {"role": "system", "content": "B"},
            {"role": "user", "content": "Hi"},
        ])
        assert system == "A\n\nB"
        assert len(rest) == 1

    def test_split_system_none_present(self):
        system, rest = AnthropicClient.split_system([{"role": "user", "content": "Hi"}])
        assert system == ""
        assert len(rest) == 1

    def test_health_check_false_without_key(self, monkeypatch):
        client = AnthropicClient(api_key="")
        client._api_key = ""
        assert client.health_check() is False

    def test_default_model(self):
        assert AnthropicClient().model == "claude-opus-4-8"

    def test_sdk_client_lazy(self):
        client = AnthropicClient(api_key="test-key")
        assert client._sdk_client is None  # not constructed until first use


class TestOpenAICompatAuth:
    def test_api_key_sets_authorization_header(self):
        client = OpenAICompatClient(api_key="sk-test")
        assert client._client.headers.get("authorization") == "Bearer sk-test"

    def test_lmstudio_without_key_has_no_auth_header(self):
        client = LMStudioClient()
        assert "authorization" not in client._client.headers
