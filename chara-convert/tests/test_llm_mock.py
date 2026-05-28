"""Tests for LLMClient ABC + MockLLMClient (PR 4 cut-4a)."""

from __future__ import annotations

import pytest

from chara_convert.llm import LLMClient, MockLLMClient


def test_llm_client_is_abstract() -> None:
    with pytest.raises(TypeError):
        LLMClient()  # type: ignore[abstract]


def test_mock_default_returns_constant_string() -> None:
    client = MockLLMClient()
    assert client.complete("anything") == "mock response"


def test_mock_with_fixed_string_returns_it_for_any_prompt() -> None:
    client = MockLLMClient(responses="canned")
    assert client.complete("foo") == "canned"
    assert client.complete("bar") == "canned"


def test_mock_with_dict_matches_by_substring() -> None:
    client = MockLLMClient(responses={"reclassify": "INSTRUCTION", "expand bio": "long bio"})
    assert client.complete("Please reclassify this paragraph") == "INSTRUCTION"
    assert client.complete("expand bio for Alice") == "long bio"


def test_mock_with_dict_raises_on_no_match() -> None:
    client = MockLLMClient(responses={"reclassify": "x"})
    with pytest.raises(KeyError):
        client.complete("totally unrelated prompt")


def test_mock_with_callable_invokes_it() -> None:
    client = MockLLMClient(responses=lambda p: p.upper())
    assert client.complete("hello") == "HELLO"


def test_mock_records_call_log() -> None:
    client = MockLLMClient()
    client.complete("first")
    client.complete("second")
    assert client.call_log == ["first", "second"]


def test_mock_complete_accepts_max_tokens_and_temperature() -> None:
    client = MockLLMClient(responses="ok")
    # Just verify signature accepts kwargs without error.
    assert client.complete("p", max_tokens=128, temperature=0.2) == "ok"
