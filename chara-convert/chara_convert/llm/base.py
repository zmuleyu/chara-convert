"""LLMClient abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Sync text-completion contract for chara-convert AI tasks.

    Implementations may wrap a remote API (Anthropic, OpenAI, Workers proxy)
    or be a deterministic mock for tests. All AI-assisted parser paths accept
    an injected ``LLMClient`` and must behave heuristically when given ``None``.
    """

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Return the model's completion for ``prompt``.

        ``max_tokens`` caps the response length; ``temperature`` controls
        sampling randomness. Implementations are free to clamp either to
        provider-supported ranges.
        """
