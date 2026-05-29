"""OpenRouter client.

The OpenAI Python SDK speaks OR's API verbatim at base_url=https://openrouter.ai/api/v1.
The class exposes two interfaces:

- complete(prompt, ...) -> str (LLMClient contract). Used by CLI / dev paths.
- stream_chat(messages, ...) async generator (Task 4). Used by API route.

Model selection is *eager* at construction time -- the class is bound to one
model_class ("low" | "high") and the OR fallback chain lives in MODEL_BY_CLASS.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Literal

from chara_convert.llm.base import LLMClient

ModelClass = Literal["low", "high"]

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# Mirrors spec Model config (frozen). primary == fallback[0] is invariant.
MODEL_BY_CLASS: dict[ModelClass, dict[str, Any]] = {
    "low": {
        "primary": "deepseek/deepseek-chat",
        "fallback": ["deepseek/deepseek-chat", "moonshotai/kimi-k2"],
    },
    "high": {
        "primary": "anthropic/claude-3.5-sonnet",
        "fallback": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
    },
}


def _default_factory(**kwargs: Any) -> Any:
    import openai
    return openai.OpenAI(**kwargs)


class OpenRouterClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_class: ModelClass = "low",
        base_url: str | None = None,
        _client_factory: Callable[..., Any] = _default_factory,
    ) -> None:
        resolved = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not resolved:
            raise ValueError("OPENROUTER_API_KEY is not set and no api_key was passed.")
        self._model_class: ModelClass = model_class
        self._cfg = MODEL_BY_CLASS[model_class]
        self._client = _client_factory(
            api_key=resolved,
            base_url=base_url or DEFAULT_BASE_URL,
        )

    @property
    def model_class(self) -> ModelClass:
        return self._model_class

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        resp = self._client.chat.completions.create(
            model=self._cfg["primary"],
            models=self._cfg["fallback"],
            extra_body={"provider": {"sort": "price", "allow_fallbacks": True}},
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        return getattr(choices[0].message, "content", "") or ""
