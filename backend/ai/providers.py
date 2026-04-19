"""LLM provider abstraction.

Swapping providers is a one-line change in env (`AI_PROVIDER`). Tests use
`NullProvider` which returns deterministic canned output, so the full AI
flow is exercisable without an actual model.
"""

from abc import ABC, abstractmethod
import re
from typing import Iterable, Optional

from config import get_env


class LLMProvider(ABC):
    """Minimum surface every AI backend must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable identifier for logging/UI."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier for logging/UI."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return a single completion string for the given prompt."""

    @abstractmethod
    def stream_complete(self, prompt: str) -> Iterable[str]:
        """Yield completion chunks for the given prompt."""


def _chunk_text(text: str) -> Iterable[str]:
    for match in re.finditer(r"\S+\s*|\s+", text):
        chunk = match.group(0)
        if chunk:
            yield chunk


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible HTTP client; works against LM Studio and api.openai.com."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ):
        self.base_url = base_url or get_env("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
        self.api_key = api_key or get_env("OPENAI_API_KEY", "lm-studio")
        self.model = model or get_env("LM_STUDIO_MODEL") or get_env("OPENAI_MODEL", "local-model")
        self.max_tokens = max_tokens

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    @property
    def model_name(self) -> str:
        return self.model

    def complete(self, prompt: str) -> str:
        # Imported lazily so `NullProvider` users don't need the SDK installed.
        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    def stream_complete(self, prompt: str) -> Iterable[str]:
        # Imported lazily so `NullProvider` users don't need the SDK installed.
        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        stream = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
            stream=True,
        )
        for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta.content or ""
            if delta:
                yield delta


class NullProvider(LLMProvider):
    """Canned-response provider for tests and offline demos.

    When used in tests, callers can inject a fixed response or a callable that
    receives the prompt and returns a string.
    """

    def __init__(self, response=None):
        self.response = response

    @property
    def provider_name(self) -> str:
        return "null"

    @property
    def model_name(self) -> str:
        return "null-provider"

    def complete(self, prompt: str) -> str:
        if callable(self.response):
            return self.response(prompt)
        if isinstance(self.response, str):
            return self.response
        # Default: echo a recognizable stub so tests can assert shape.
        snippet = prompt.strip().splitlines()[-1][:80] if prompt.strip() else ""
        return f"[null-provider] {snippet}"

    def stream_complete(self, prompt: str) -> Iterable[str]:
        yield from _chunk_text(self.complete(prompt))


def get_provider() -> LLMProvider:
    name = (get_env("AI_PROVIDER", "null") or "null").lower()
    if name == "openai":
        return OpenAIProvider()
    return NullProvider()
