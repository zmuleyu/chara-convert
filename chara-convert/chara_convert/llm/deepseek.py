"""DeepSeek API binding for :class:`LLMClient`.

DeepSeek exposes an OpenAI-compatible Chat Completions API at
``https://api.deepseek.com``, so we reuse the ``openai`` SDK (optional
dependency ``chara-convert[deepseek]``). Tests inject a fake client via the
``_client_factory`` kwarg to verify the contract without the real SDK.

DeepSeek is positioned as the cheap dev/staging backend (~$0.14/M input tokens
as of 2026-05) — set ``DEEPSEEK_API_KEY`` to use it, leaving
``ANTHROPIC_API_KEY`` for prod-grade runs.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from chara_convert.llm.base import LLMClient

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"


def _default_factory(**kwargs: Any) -> Any:
    try:
        import openai  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "openai SDK is required for DeepSeekClient. "
            "Install with: pip install 'chara-convert[deepseek]' (or `pip install openai`)"
        ) from e
    return openai.OpenAI(**kwargs)


class DeepSeekClient(LLMClient):
    """DeepSeek Chat Completions API client.

    Reads ``DEEPSEEK_API_KEY`` from the environment when ``api_key`` is not
    supplied. ``base_url`` defaults to ``https://api.deepseek.com``; pass a
    custom value to point at a proxy or alternative OpenAI-compatible endpoint.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
        _client_factory: Callable[..., Any] = _default_factory,
    ) -> None:
        resolved = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not resolved:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set and no api_key was passed to DeepSeekClient."
            )
        self._model = model
        self._client = _client_factory(
            api_key=resolved,
            base_url=base_url or DEFAULT_BASE_URL,
        )

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        return getattr(choices[0].message, "content", "") or ""
