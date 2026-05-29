from typing import Any

from chara_convert.llm.openrouter import OpenRouterClient


class _FakeChatCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [
            type("c", (), {"message": type("m", (), {"content": content})()})()
        ]


class _FakeOpenAI:
    """Stands in for openai.OpenAI; captures kwargs and returns canned content."""
    def __init__(self, content: str = "ok"):
        self.content = content
        self.calls: list[dict[str, Any]] = []
        self.chat = type("ns", (), {"completions": self})()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeChatCompletion(self.content)


def test_complete_calls_or_with_low_class_primary():
    fake = _FakeOpenAI(content="hello world")
    c = OpenRouterClient(
        api_key="sk-or-test",
        model_class="low",
        _client_factory=lambda **_: fake,
    )
    out = c.complete("hi", max_tokens=20, temperature=0.5)
    assert out == "hello world"
    assert len(fake.calls) == 1
    kwargs = fake.calls[0]
    assert kwargs["model"] == "deepseek/deepseek-chat"
    assert kwargs["models"] == ["deepseek/deepseek-chat", "moonshotai/kimi-k2"]
    assert kwargs["max_tokens"] == 20
    assert kwargs["temperature"] == 0.5
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


def test_complete_high_class_uses_claude_primary():
    fake = _FakeOpenAI(content="x")
    c = OpenRouterClient(
        api_key="sk-or-test", model_class="high",
        _client_factory=lambda **_: fake,
    )
    c.complete("hi")
    assert fake.calls[0]["model"] == "anthropic/claude-3.5-sonnet"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    import pytest
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(api_key=None, model_class="low")
