"""Tests for DeepSeekClient.

DeepSeek API is OpenAI-compatible. We use the openai SDK (optional dep, exposed
via ``chara-convert[deepseek]`` extra) but inject a fake client factory so the
contract can be verified without installing the real SDK.
"""

from __future__ import annotations

from typing import Any

import pytest

from chara_convert.llm.deepseek import DEFAULT_MODEL, DeepSeekClient


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = text


class _FakeChoice:
    def __init__(self, text: str) -> None:
        self.message = _FakeMessage(text)


class _FakeCompletion:
    def __init__(self, text: str) -> None:
        self.choices = [_FakeChoice(text)]


class _FakeCompletions:
    def __init__(self, recorder: dict[str, Any]) -> None:
        self._recorder = recorder

    def create(self, **kwargs: Any) -> _FakeCompletion:
        self._recorder.update(kwargs)
        return _FakeCompletion("fake deepseek completion")


class _FakeChat:
    def __init__(self, recorder: dict[str, Any]) -> None:
        self.completions = _FakeCompletions(recorder)


class _FakeOpenAI:
    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.recorder: dict[str, Any] = {}
        self.chat = _FakeChat(self.recorder)


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekClient()


def test_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
    fake = _FakeOpenAI(api_key="env-key")
    client = DeepSeekClient(_client_factory=lambda **kw: fake)
    assert client._client is fake
    assert fake.api_key == "env-key"


def test_explicit_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
    captured: dict[str, Any] = {}

    def factory(**kw: Any) -> _FakeOpenAI:
        captured.update(kw)
        return _FakeOpenAI(**kw)

    DeepSeekClient(api_key="explicit-key", _client_factory=factory)
    assert captured["api_key"] == "explicit-key"


def test_default_base_url_points_at_deepseek() -> None:
    captured: dict[str, Any] = {}

    def factory(**kw: Any) -> _FakeOpenAI:
        captured.update(kw)
        return _FakeOpenAI(**kw)

    DeepSeekClient(api_key="k", _client_factory=factory)
    assert captured["base_url"] == "https://api.deepseek.com"


def test_custom_base_url_overrides_default() -> None:
    captured: dict[str, Any] = {}

    def factory(**kw: Any) -> _FakeOpenAI:
        captured.update(kw)
        return _FakeOpenAI(**kw)

    DeepSeekClient(api_key="k", base_url="https://proxy.example.com", _client_factory=factory)
    assert captured["base_url"] == "https://proxy.example.com"


def test_complete_calls_chat_completions_with_prompt() -> None:
    fake = _FakeOpenAI(api_key="k")
    client = DeepSeekClient(api_key="k", model="deepseek-chat", _client_factory=lambda **kw: fake)
    out = client.complete("hello world", max_tokens=512, temperature=0.3)
    assert out == "fake deepseek completion"
    assert fake.recorder["model"] == "deepseek-chat"
    assert fake.recorder["max_tokens"] == 512
    assert fake.recorder["temperature"] == 0.3
    assert fake.recorder["messages"] == [{"role": "user", "content": "hello world"}]


def test_default_model_is_deepseek_chat() -> None:
    assert DEFAULT_MODEL == "deepseek-chat"


def test_missing_openai_sdk_raises_install_hint() -> None:
    """If user sets DEEPSEEK_API_KEY but didn't install the [deepseek] extra,
    the SDK import fails. The library re-raises with an install hint instead
    of a bare ImportError.
    """

    def fake_factory(**_kw: Any) -> Any:
        raise ImportError(
            "openai SDK is required for DeepSeekClient. "
            "Install with: pip install 'chara-convert[deepseek]' (or `pip install openai`)"
        )

    with pytest.raises(ImportError, match=r"chara-convert\[deepseek\]"):
        DeepSeekClient(api_key="k", _client_factory=fake_factory)
