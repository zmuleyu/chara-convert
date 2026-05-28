"""LLM backend factory shared by CLI and WebUI.

This module isolates the env-var precedence rules from any UI framework so
both ``chara_convert.cli`` (Click) and ``chara_convert.webui`` (Gradio) can
build a client without importing each other's dependencies.
"""

from __future__ import annotations

import os

from chara_convert.llm.base import LLMClient
from chara_convert.llm.mock import MockLLMClient

Status = str  # "mock" | "anthropic" | "none"


def build_ai_client_or_none() -> tuple[LLMClient | None, Status]:
    """Resolve an :class:`LLMClient` from environment variables.

    Precedence:

    1. ``CHARA_CONVERT_AI_MOCK`` — wraps the value as a canned
       :class:`MockLLMClient` response. Used by tests and offline smoke runs.
    2. ``ANTHROPIC_API_KEY`` — instantiates :class:`AnthropicClient`. The
       ``anthropic`` SDK import is deferred so callers without the ``[ai]``
       extra (or in test envs) only pay for it when they actually need it.

    Returns ``(client, status)`` where ``status`` is a human-readable label
    (``"mock"`` / ``"anthropic"`` / ``"none"``) suitable for UI display.
    ``client`` is ``None`` exactly when ``status == "none"``.
    """
    mock = os.environ.get("CHARA_CONVERT_AI_MOCK")
    if mock is not None:
        return MockLLMClient(responses=mock), "mock"
    if os.environ.get("ANTHROPIC_API_KEY"):
        from chara_convert.llm.anthropic import AnthropicClient

        base_url = os.environ.get("CHARA_CONVERT_API_BASE") or None
        return AnthropicClient(base_url=base_url), "anthropic"
    return None, "none"
