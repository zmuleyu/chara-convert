"""LLM backend factory shared by CLI and WebUI.

This module isolates the env-var precedence rules from any UI framework so
both ``chara_convert.cli`` (Click) and ``chara_convert.webui`` (Gradio) can
build a client without importing each other's dependencies.
"""

from __future__ import annotations

import os

from chara_convert.llm.base import LLMClient
from chara_convert.llm.mock import MockLLMClient

Status = str  # "mock" | "openrouter" | "anthropic" | "deepseek" | "none"


def build_ai_client_or_none() -> tuple[LLMClient | None, Status]:
    """Resolve an :class:`LLMClient` from environment variables.

    Precedence:

    1. ``CHARA_CONVERT_AI_MOCK`` — wraps the value as a canned
       :class:`MockLLMClient` response. Used by tests and offline smoke runs.
    2. ``OPENROUTER_API_KEY`` — instantiates :class:`OpenRouterClient`
       (prod backend after Phase B). Class defaults to ``low`` for CLI/dev;
       the API route bypasses the factory and calls ``router.plan_request()``
       for per-request class selection.
    3. ``ANTHROPIC_API_KEY`` — instantiates :class:`AnthropicClient` (legacy
       backend; Sonnet / Haiku). Retained behind OR so existing dev
       environments keep working.
    4. ``DEEPSEEK_API_KEY`` — instantiates :class:`DeepSeekClient` (legacy
       cheap dev/staging backend, OpenAI-compatible).

    Returns ``(client, status)`` where ``status`` is a human-readable label
    (``"mock"`` / ``"openrouter"`` / ``"anthropic"`` / ``"deepseek"`` /
    ``"none"``) suitable for UI display. ``client`` is ``None`` exactly when
    ``status == "none"``.
    """
    mock = os.environ.get("CHARA_CONVERT_AI_MOCK")
    if mock is not None:
        return MockLLMClient(responses=mock), "mock"
    if os.environ.get("OPENROUTER_API_KEY"):
        from chara_convert.llm.openrouter import OpenRouterClient

        # CLI/dev default is "low" — cheaper smoke runs. API route uses
        # router.plan_request() per request and bypasses the factory.
        model_class = os.environ.get("CHARA_CONVERT_OR_CLASS", "low")
        return OpenRouterClient(model_class=model_class), "openrouter"  # type: ignore[arg-type]
    if os.environ.get("ANTHROPIC_API_KEY"):
        from chara_convert.llm.anthropic import DEFAULT_MODEL, AnthropicClient

        base_url = os.environ.get("CHARA_CONVERT_API_BASE") or None
        model = os.environ.get("CHARA_CONVERT_MODEL") or DEFAULT_MODEL
        return AnthropicClient(base_url=base_url, model=model), "anthropic"
    if os.environ.get("DEEPSEEK_API_KEY"):
        from chara_convert.llm.deepseek import DEFAULT_MODEL, DeepSeekClient

        base_url = os.environ.get("CHARA_CONVERT_API_BASE") or None
        model = os.environ.get("CHARA_CONVERT_MODEL") or DEFAULT_MODEL
        return DeepSeekClient(base_url=base_url, model=model), "deepseek"
    return None, "none"
