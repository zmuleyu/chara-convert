"""Anthropic Claude API binding for :class:`LLMClient`.

The ``anthropic`` SDK is an optional dependency (``chara-convert[ai]``); this
module raises a clear installation hint if the SDK is missing at instantiation
time. Tests inject a fake client via the ``_client_factory`` kwarg to verify
the contract without requiring the real SDK.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from chara_convert.llm.base import LLMClient

DEFAULT_MODEL = "claude-haiku-4-5"


def _default_factory(**kwargs: Any) -> Any:
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "anthropic SDK is required for AnthropicClient. "
            "Install with: pip install 'chara-convert[ai]' (or `pip install anthropic`)"
        ) from e
    return anthropic.Anthropic(**kwargs)


class AnthropicClient(LLMClient):
    """Direct Anthropic Claude API client.

    Reads ``ANTHROPIC_API_KEY`` from the environment when ``api_key`` is not
    supplied. ``base_url`` can point at a proxy (e.g. aichathub Workers) that
    speaks the Anthropic Messages protocol.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
        _client_factory: Callable[..., Any] = _default_factory,
    ) -> None:
        resolved = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set and no api_key was passed to AnthropicClient."
            )
        self._model = model
        kwargs: dict[str, Any] = {"api_key": resolved}
        if base_url is not None:
            kwargs["base_url"] = base_url
        default_headers: dict[str, str] = {}
        proxy_token = os.environ.get("CHARA_CONVERT_PROXY_AUTH_TOKEN")
        if proxy_token:
            default_headers["X-Creem-Token"] = proxy_token
        proxy_origin = os.environ.get("CHARA_CONVERT_PROXY_ORIGIN")
        if proxy_origin:
            default_headers["Origin"] = proxy_origin
        if default_headers:
            kwargs["default_headers"] = default_headers
        self._client = _client_factory(**kwargs)

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        # Anthropic returns a list of content blocks; concatenate text blocks.
        parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts)
