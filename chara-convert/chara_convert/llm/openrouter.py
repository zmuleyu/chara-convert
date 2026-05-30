"""OpenRouter client.

The OpenAI Python SDK speaks OR's API verbatim at base_url=https://openrouter.ai/api/v1.
The class exposes two interfaces:

- complete(prompt, ...) -> str (LLMClient contract). Used by CLI / dev paths.
- stream_chat(messages, ...) async generator (Task 4). Used by API route.

Model selection is *eager* at construction time -- the class is bound to one
model_class ("low" | "high") and the OR fallback chain lives in MODEL_BY_CLASS.
"""
from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator, Callable
from typing import Any, Literal

import httpx

from chara_convert.llm.base import LLMClient

ModelClass = Literal["low", "high"]

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# Mirrors spec Model config (frozen). primary == fallback[0] is invariant.
# Slugs must exist in OR's live list — pricing.py PRICING_TABLE and the
# scripts/pricing_drift_check.py drift guard both pivot on these strings.
MODEL_BY_CLASS: dict[ModelClass, dict[str, Any]] = {
    "low": {
        "primary": "deepseek/deepseek-chat",
        "fallback": ["deepseek/deepseek-chat", "moonshotai/kimi-k2"],
    },
    "high": {
        "primary": "anthropic/claude-sonnet-4.6",
        "fallback": ["anthropic/claude-sonnet-4.6", "openai/gpt-4o"],
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

    def _ensure_async_http(self) -> Any:
        existing = getattr(self, "_async_http", None)
        if existing is not None:
            return existing
        self._async_http = httpx.AsyncClient(
            base_url=DEFAULT_BASE_URL,
            headers={
                "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY') or ''}",
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        return self._async_http

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 800,
        temperature: float = 0.7,
    ) -> AsyncGenerator[dict[str, Any], None]:
        http = self._ensure_async_http()
        payload = {
            "model": self._cfg["primary"],
            "models": self._cfg["fallback"],
            "provider": {"sort": "price", "allow_fallbacks": True},
            "messages": messages,
            "stream": True,
            "usage": {"include": True},
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with http.stream("POST", "/chat/completions", json=payload) as response:
            buf = b""
            async for chunk in response.aiter_bytes():
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    ev = parse_or_sse_line(line)
                    if ev is not None:
                        yield ev
            if buf:
                ev = parse_or_sse_line(buf)
                if ev is not None:
                    yield ev


def parse_or_sse_line(raw: bytes) -> dict[str, Any] | None:
    """Convert one OR SSE line to our internal event shape, or None for non-data."""
    if not raw.startswith(b"data:"):
        return None
    payload = raw[len(b"data:"):].strip()
    if not payload:
        return None
    if payload == b"[DONE]":
        return {"type": "done"}
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return None
    usage = obj.get("usage") or {}
    if isinstance(usage, dict) and "cost" in usage:
        return {"type": "usage", "cost_usd": float(usage["cost"])}
    choices = obj.get("choices") or []
    if choices:
        delta = (choices[0].get("delta") or {}).get("content")
        if delta is not None:
            return {"type": "content", "delta": delta}
    return None
