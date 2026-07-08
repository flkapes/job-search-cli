"""Unified LLM client: Ollama, LM Studio, Anthropic, and OpenAI-compatible backends."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Generator

import httpx

from codepractice.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    DEBUG,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)


class LLMClient(ABC):
    """Abstract base for LLM backends."""

    @abstractmethod
    def health_check(self) -> bool:
        ...

    @abstractmethod
    def chat_sync(self, messages: list[dict], **kwargs) -> str:
        ...

    @abstractmethod
    def stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        ...

    def list_models(self) -> list[str]:
        return []


class OllamaClient(LLMClient):
    """Ollama backend — uses the REST API directly for maximum compatibility."""

    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=LLM_TIMEOUT)

    def health_check(self) -> bool:
        try:
            resp = self._client.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = self._client.get(f"{self.base_url}/api/tags", timeout=5)
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def chat_sync(self, messages: list[dict], **kwargs) -> str:
        if DEBUG:
            print(f"[DEBUG] Ollama chat: {json.dumps(messages, indent=2)[:500]}")
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": kwargs.get("temperature", 0.7)},
        }
        for attempt in range(LLM_MAX_RETRIES):
            try:
                resp = self._client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=LLM_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"]
            except Exception as e:
                if attempt == LLM_MAX_RETRIES - 1:
                    raise LLMError(f"Ollama request failed: {e}") from e
        return ""

    def stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": kwargs.get("temperature", 0.7)},
        }
        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=LLM_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise LLMError(f"Ollama stream failed: {e}") from e


class LMStudioClient(LLMClient):
    """LM Studio backend — OpenAI-compatible API."""

    def __init__(
        self,
        model: str = LMSTUDIO_MODEL,
        base_url: str = LMSTUDIO_BASE_URL,
        api_key: str = "",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(timeout=LLM_TIMEOUT, headers=headers)

    def health_check(self) -> bool:
        try:
            resp = self._client.get(f"{self.base_url}/models", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = self._client.get(f"{self.base_url}/models", timeout=5)
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def chat_sync(self, messages: list[dict], **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False,
        }
        for attempt in range(LLM_MAX_RETRIES):
            try:
                resp = self._client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=LLM_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == LLM_MAX_RETRIES - 1:
                    raise LLMError(f"LM Studio request failed: {e}") from e
        return ""

    def stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
        }
        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=LLM_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    raw = line.removeprefix("data: ").strip()
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                        token = data["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except Exception as e:
            raise LLMError(f"LM Studio stream failed: {e}") from e


class OpenAICompatClient(LMStudioClient):
    """OpenAI (or any OpenAI-compatible cloud endpoint) — API key from the environment."""

    def __init__(
        self,
        model: str = OPENAI_MODEL,
        base_url: str = OPENAI_BASE_URL,
        api_key: str = "",
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url,
            api_key=api_key or OPENAI_API_KEY,
        )


class AnthropicClient(LLMClient):
    """Anthropic API backend via the official SDK. Reads ANTHROPIC_API_KEY from .env."""

    def __init__(self, model: str = ANTHROPIC_MODEL, api_key: str = "") -> None:
        self.model = model
        self._api_key = api_key or ANTHROPIC_API_KEY
        self._sdk_client = None

    @property
    def _client(self):
        if self._sdk_client is None:
            try:
                import anthropic
            except ImportError as e:
                raise LLMError(
                    "The 'anthropic' package is required for the anthropic backend "
                    "(pip install anthropic)"
                ) from e
            self._sdk_client = anthropic.Anthropic(
                api_key=self._api_key or None, timeout=LLM_TIMEOUT
            )
        return self._sdk_client

    @staticmethod
    def split_system(messages: list[dict]) -> tuple[str, list[dict]]:
        """Anthropic takes the system prompt as a separate parameter."""
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        return "\n\n".join(system_parts), rest

    def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            self._client.models.retrieve(self.model)
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            return [m.id for m in self._client.models.list()]
        except Exception:
            return []

    def chat_sync(self, messages: list[dict], **kwargs) -> str:
        system, rest = self.split_system(messages)
        try:
            # Current Claude models reject sampling params — steer via prompts only.
            response = self._client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system or None,
                messages=rest,
            )
            return next((b.text for b in response.content if b.type == "text"), "")
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Anthropic request failed: {e}") from e

    def stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        system, rest = self.split_system(messages)
        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system or None,
                messages=rest,
            ) as stream:
                yield from stream.text_stream
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Anthropic stream failed: {e}") from e


class LLMError(Exception):
    """Raised when LLM backend is unreachable or returns an error."""


def get_client(backend: str | None = None, model: str | None = None, base_url: str | None = None) -> LLMClient:
    """Factory: create the appropriate LLM client."""
    from codepractice.config import LLM_BACKEND

    backend = backend or LLM_BACKEND

    if backend == "lmstudio":
        return LMStudioClient(
            model=model or LMSTUDIO_MODEL,
            base_url=base_url or LMSTUDIO_BASE_URL,
        )
    if backend == "anthropic":
        return AnthropicClient(model=model or ANTHROPIC_MODEL)
    if backend == "openai":
        return OpenAICompatClient(
            model=model or OPENAI_MODEL,
            base_url=base_url or OPENAI_BASE_URL,
        )
    return OllamaClient(
        model=model or OLLAMA_MODEL,
        base_url=base_url or OLLAMA_BASE_URL,
    )


# ── JSON extraction helper ─────────────────────────────────────────────────────

def extract_json(text: str) -> dict | list | None:
    """Extract JSON from LLM output that may contain markdown fences."""
    # Try raw parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } or [ ... ]
    for pattern in (r"\{[\s\S]+\}", r"\[[\s\S]+\]"):
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    return None
