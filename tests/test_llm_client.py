"""Tests for LLM client utilities (pure logic, no network calls)."""

from __future__ import annotations

from codepractice.llm.client import LLMError, extract_json, get_client


class TestExtractJson:
    def test_raw_object(self):
        result = extract_json('{"score": 0.8, "passed": true}')
        assert result == {"score": 0.8, "passed": True}

    def test_raw_array(self):
        result = extract_json('[{"a": 1}, {"b": 2}]')
        assert result == [{"a": 1}, {"b": 2}]

    def test_markdown_json_fence(self):
        text = '```json\n{"score": 0.9}\n```'
        result = extract_json(text)
        assert result == {"score": 0.9}

    def test_plain_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_embedded_object_in_text(self):
        text = 'Here is my analysis.\n{"score": 0.75, "passed": true}\nEnd.'
        result = extract_json(text)
        assert isinstance(result, dict)
        assert result["score"] == 0.75

    def test_embedded_array_in_text(self):
        text = 'Problems:\n[{"title": "Two Sum"}, {"title": "Max Subarray"}]'
        result = extract_json(text)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_none_for_plain_text(self):
        result = extract_json("This is just a plain string with no JSON.")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = extract_json("")
        assert result is None

    def test_returns_none_for_malformed_json(self):
        result = extract_json("{not valid json}")
        assert result is None

    def test_nested_object(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = extract_json(text)
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_integer_values(self):
        result = extract_json('{"count": 42, "flag": false}')
        assert result["count"] == 42
        assert result["flag"] is False

    def test_prefers_raw_parse_over_regex(self):
        """Valid JSON should be parsed directly without regex fallback."""
        result = extract_json('{"score": 1.0}')
        assert result == {"score": 1.0}


class TestGetClient:
    def test_default_returns_ollama(self):
        from codepractice.llm.client import OllamaClient
        client = get_client(backend="ollama")
        assert isinstance(client, OllamaClient)

    def test_lmstudio_backend(self):
        from codepractice.llm.client import LMStudioClient
        client = get_client(backend="lmstudio")
        assert isinstance(client, LMStudioClient)

    def test_custom_model_applied(self):
        client = get_client(backend="ollama", model="codellama")
        assert client.model == "codellama"

    def test_custom_base_url_applied(self):
        client = get_client(backend="ollama", base_url="http://myserver:11434")
        assert "myserver" in client.base_url

    def test_unknown_backend_defaults_to_ollama(self):
        from codepractice.llm.client import OllamaClient
        client = get_client(backend="unknown_backend")
        assert isinstance(client, OllamaClient)


class TestLLMError:
    def test_is_exception(self):
        err = LLMError("connection refused")
        assert isinstance(err, Exception)
        assert "connection refused" in str(err)
