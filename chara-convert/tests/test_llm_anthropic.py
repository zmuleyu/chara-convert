"""Tests for AnthropicClient (PR 4 cut-4a).

The ``anthropic`` SDK itself is not a hard dependency of chara-convert; these
tests inject a fake client factory so the contract can be verified without the
real SDK installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from chara_convert.llm.anthropic import AnthropicClient


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [type("Block", (), {"type": "text", "text": text})()]


class _FakeMessages:
    def __init__(self, recorder: dict[str, Any]) -> None:
        self._recorder = recorder

    def create(self, **kwargs: Any) -> _FakeMessage:
        self._recorder.update(kwargs)
        return _FakeMessage("fake completion")


class _FakeAnthropic:
    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.recorder: dict[str, Any] = {}
        self.messages = _FakeMessages(self.recorder)


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicClient()


def test_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    fake = _FakeAnthropic(api_key="env-key")
    client = AnthropicClient(_client_factory=lambda **kw: fake)
    assert client._client is fake
    assert fake.api_key == "env-key"


def test_explicit_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    captured: dict[str, Any] = {}

    def factory(**kw: Any) -> _FakeAnthropic:
        captured.update(kw)
        return _FakeAnthropic(**kw)

    AnthropicClient(api_key="explicit-key", _client_factory=factory)
    assert captured["api_key"] == "explicit-key"


def test_complete_calls_messages_create_with_prompt() -> None:
    fake = _FakeAnthropic(api_key="k")
    client = AnthropicClient(api_key="k", model="claude-haiku-4-5", _client_factory=lambda **kw: fake)
    out = client.complete("hello world", max_tokens=512, temperature=0.3)
    assert out == "fake completion"
    assert fake.recorder["model"] == "claude-haiku-4-5"
    assert fake.recorder["max_tokens"] == 512
    assert fake.recorder["temperature"] == 0.3
    assert fake.recorder["messages"] == [{"role": "user", "content": "hello world"}]


def test_base_url_passed_through() -> None:
    captured: dict[str, Any] = {}

    def factory(**kw: Any) -> _FakeAnthropic:
        captured.update(kw)
        return _FakeAnthropic(**kw)

    AnthropicClient(api_key="k", base_url="https://proxy.example.com", _client_factory=factory)
    assert captured["base_url"] == "https://proxy.example.com"


def _capture_factory() -> tuple[dict[str, Any], Any]:
    captured: dict[str, Any] = {}

    def factory(**kw: Any) -> Any:
        captured.update(kw)
        return type("Stub", (), {"messages": _FakeMessages({})})()

    return captured, factory


def test_proxy_auth_token_injects_creem_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHARA_CONVERT_PROXY_AUTH_TOKEN", "tk-abc")
    monkeypatch.delenv("CHARA_CONVERT_PROXY_ORIGIN", raising=False)
    captured, factory = _capture_factory()
    AnthropicClient(api_key="k", _client_factory=factory)
    assert captured["default_headers"] == {"X-Creem-Token": "tk-abc"}


def test_proxy_origin_only_injects_origin_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHARA_CONVERT_PROXY_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CHARA_CONVERT_PROXY_ORIGIN", "https://aichathub.uk")
    captured, factory = _capture_factory()
    AnthropicClient(api_key="k", _client_factory=factory)
    assert captured["default_headers"] == {"Origin": "https://aichathub.uk"}


def test_proxy_token_and_origin_both_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHARA_CONVERT_PROXY_AUTH_TOKEN", "tk-abc")
    monkeypatch.setenv("CHARA_CONVERT_PROXY_ORIGIN", "https://aichathub.uk")
    captured, factory = _capture_factory()
    AnthropicClient(api_key="k", _client_factory=factory)
    assert captured["default_headers"] == {
        "X-Creem-Token": "tk-abc",
        "Origin": "https://aichathub.uk",
    }


def test_no_proxy_envs_omits_default_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHARA_CONVERT_PROXY_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_PROXY_ORIGIN", raising=False)
    captured, factory = _capture_factory()
    AnthropicClient(api_key="k", _client_factory=factory)
    assert "default_headers" not in captured


def test_missing_anthropic_sdk_raises_install_hint() -> None:
    """Pin the actionable ImportError message in anthropic.py:_default_factory.

    If a user sets ANTHROPIC_API_KEY but didn't install the `[ai]` extra, the
    SDK import fails. The library re-raises with an install hint instead of
    leaking a bare ImportError traceback. This test prevents that hint from
    silently disappearing in future refactors.
    """

    def fake_factory(**_kw: Any) -> Any:
        raise ImportError(
            "anthropic SDK is required for AnthropicClient. "
            "Install with: pip install 'chara-convert[ai]' (or `pip install anthropic`)"
        )

    with pytest.raises(ImportError, match=r"chara-convert\[ai\]"):
        AnthropicClient(api_key="k", _client_factory=fake_factory)
