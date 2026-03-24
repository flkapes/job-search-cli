"""Unified LLM client: Ollama + LM Studio backends with streaming support."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Generator

import httpx

from codepractice.config import (
    DEBUG,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
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

    def __init__(self, model: str = LMSTUDIO_MODEL, base_url: str = LMSTUDIO_BASE_URL) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=LLM_TIMEOUT)

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
