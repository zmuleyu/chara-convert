"""MockLLMClient for unit tests and AI-disabled CLI paths."""

from __future__ import annotations

from collections.abc import Callable

from chara_convert.llm.base import LLMClient

Responses = str | dict[str, str] | Callable[[str], str]


class MockLLMClient(LLMClient):
    """Deterministic ``LLMClient`` for tests.

    ``responses`` controls behavior:

    - ``str``: returned verbatim for any prompt (default ``"mock response"``).
    - ``dict[str, str]``: first key found as a substring of the prompt wins;
      raises :class:`KeyError` if no key matches.
    - ``Callable[[str], str]``: invoked with the prompt; its return is the
      completion.

    Every call is appended to :attr:`call_log` for assertion in tests.
    """

    def __init__(self, responses: Responses = "mock response") -> None:
        self._responses = responses
        self.call_log: list[str] = []

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        self.call_log.append(prompt)
        responses = self._responses
        if isinstance(responses, str):
            return responses
        if callable(responses):
            return responses(prompt)
        # dict[str, str] — substring match in insertion order.
        for needle, reply in responses.items():
            if needle in prompt:
                return reply
        raise KeyError(f"MockLLMClient: no response key matched prompt: {prompt!r}")
