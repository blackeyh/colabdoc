"""LLM provider abstraction.

Swapping providers is a one-line change in env (`AI_PROVIDER`). Tests use
`NullProvider` which returns deterministic canned output, so the full AI
flow is exercisable without an actual model.
"""

from abc import ABC, abstractmethod
from typing import Optional

from config import get_env


class LLMProvider(ABC):
    """Minimum surface every AI backend must implement."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return a single completion string for the given prompt."""


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


class NullProvider(LLMProvider):
    """Canned-response provider for tests and offline demos.

    When used in tests, callers can inject a fixed response or a callable that
    receives the prompt and returns a string.
    """

    def __init__(self, response=None):
        self.response = response

    def complete(self, prompt: str) -> str:
        if callable(self.response):
            return self.response(prompt)
        if isinstance(self.response, str):
            return self.response
        # Default: echo a recognizable stub so tests can assert shape.
        snippet = prompt.strip().splitlines()[-1][:80] if prompt.strip() else ""
        return f"[null-provider] {snippet}"


def get_provider() -> LLMProvider:
    name = (get_env("AI_PROVIDER", "null") or "null").lower()
    if name == "openai":
        return OpenAIProvider()
    return NullProvider()
