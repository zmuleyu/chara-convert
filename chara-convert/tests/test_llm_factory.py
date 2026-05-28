"""Tests for chara_convert.llm.factory.build_ai_client_or_none()."""

from __future__ import annotations

from typing import Any

import pytest

import chara_convert.llm.anthropic as anthropic_module
from chara_convert.llm import MockLLMClient
from chara_convert.llm.factory import build_ai_client_or_none


def test_no_env_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """No backend env set → (None, 'none')."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client, status = build_ai_client_or_none()
    assert client is None
    assert status == "none"


def test_mock_env_returns_mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """CHARA_CONVERT_AI_MOCK set → MockLLMClient + 'mock' status."""
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "[CANNED]")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client, status = build_ai_client_or_none()
    assert isinstance(client, MockLLMClient)
    assert status == "mock"
    # Canned response is wired correctly.
    assert client.complete("any prompt") == "[CANNED]"


def test_anthropic_env_returns_anthropic_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ANTHROPIC_API_KEY set (no mock) → 'anthropic' status.

    We don't instantiate the real Anthropic SDK here; the factory must defer
    that import so test environments without the SDK still pass. We assert
    the *status* path is taken and accept that ``client`` may be a real
    instance or raise ImportError — see ``test_anthropic_no_sdk_fallback``.
    """
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    # If anthropic SDK is installed, this succeeds; if not, factory must
    # surface a clear status rather than crashing on import.
    try:
        client, status = build_ai_client_or_none()
    except ImportError:
        pytest.skip("anthropic SDK not installed; covered by other tests")
    assert client is not None
    assert status == "anthropic"


def test_mock_takes_precedence_over_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both env vars set → mock wins (matches CLI behavior)."""
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "[MOCK WINS]")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-real-key")
    client, status = build_ai_client_or_none()
    assert isinstance(client, MockLLMClient)
    assert status == "mock"


def test_api_base_env_flows_to_anthropic_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CHARA_CONVERT_API_BASE set → AnthropicClient instantiated with base_url."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CHARA_CONVERT_API_BASE", "https://aichathub.uk/api/llm/proxy")

    captured: dict[str, Any] = {}

    class _RecordingAnthropic:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(anthropic_module, "AnthropicClient", _RecordingAnthropic)

    client, status = build_ai_client_or_none()
    assert status == "anthropic"
    assert client is not None
    assert captured == {
        "base_url": "https://aichathub.uk/api/llm/proxy",
        "model": anthropic_module.DEFAULT_MODEL,
    }


def test_no_api_base_env_passes_none_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without CHARA_CONVERT_API_BASE, factory passes base_url=None (direct API)."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_API_BASE", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    captured: dict[str, Any] = {}

    class _RecordingAnthropic:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(anthropic_module, "AnthropicClient", _RecordingAnthropic)

    _client, status = build_ai_client_or_none()
    assert status == "anthropic"
    assert captured == {"base_url": None, "model": anthropic_module.DEFAULT_MODEL}


def test_chara_convert_model_env_propagates_to_anthropic_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CHARA_CONVERT_MODEL overrides DEFAULT_MODEL when set."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_API_BASE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CHARA_CONVERT_MODEL", "anthropic/claude-3.5-haiku")

    captured: dict[str, Any] = {}

    class _RecordingAnthropic:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(anthropic_module, "AnthropicClient", _RecordingAnthropic)

    _client, status = build_ai_client_or_none()
    assert status == "anthropic"
    assert captured["model"] == "anthropic/claude-3.5-haiku"


def test_empty_chara_convert_model_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty CHARA_CONVERT_MODEL is treated as unset → DEFAULT_MODEL wins."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_API_BASE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CHARA_CONVERT_MODEL", "")

    captured: dict[str, Any] = {}

    class _RecordingAnthropic:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(anthropic_module, "AnthropicClient", _RecordingAnthropic)

    _client, status = build_ai_client_or_none()
    assert status == "anthropic"
    assert captured["model"] == anthropic_module.DEFAULT_MODEL
