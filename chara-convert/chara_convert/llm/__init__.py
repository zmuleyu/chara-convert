"""LLM client abstraction layer for chara-convert.

The package-level ABC keeps AI-assisted source parsing decoupled from any
concrete provider; callers inject a :class:`LLMClient` (or ``None`` to disable
AI paths and fall back to heuristics).
"""

from __future__ import annotations

from chara_convert.llm.base import LLMClient
from chara_convert.llm.mock import MockLLMClient

__all__ = ["LLMClient", "MockLLMClient"]
