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
    assert fake.calls[0]["model"] == "anthropic/claude-sonnet-4.6"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    import pytest
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(api_key=None, model_class="low")


import asyncio  # noqa: E402

from chara_convert.llm.openrouter import parse_or_sse_line  # noqa: E402


def test_parse_or_sse_line_content_chunk():
    line = b'data: {"choices":[{"delta":{"content":"hello"}}]}'
    assert parse_or_sse_line(line) == {"type": "content", "delta": "hello"}


def test_parse_or_sse_line_usage_chunk():
    line = b'data: {"choices":[],"usage":{"total_tokens":100,"cost":0.0042}}'
    assert parse_or_sse_line(line) == {"type": "usage", "cost_usd": 0.0042}


def test_parse_or_sse_line_done_sentinel():
    assert parse_or_sse_line(b'data: [DONE]') == {"type": "done"}


def test_parse_or_sse_line_keepalive_or_blank_returns_none():
    assert parse_or_sse_line(b'') is None
    assert parse_or_sse_line(b': ping') is None


def test_stream_chat_emits_content_then_usage_then_done():
    async def run():
        async def _aiter(self):
            chunks = [
                b'data: {"choices":[{"delta":{"content":"hel"}}]}\n',
                b'data: {"choices":[{"delta":{"content":"lo"}}]}\n',
                b'data: {"choices":[],"usage":{"cost":0.001}}\n',
                b'data: [DONE]\n',
            ]
            for ch in chunks:
                yield ch

        # httpx's AsyncClient.stream() async context manager yields a Response
        # directly — there is no `.response` wrapper. Mock matches that shape.
        class _FakeResponse:
            def aiter_bytes(self):
                return _aiter(self)
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False

        class _FakeAsyncClient:
            def stream(self, *a, **k): return _FakeResponse()
            async def aclose(self): pass

        c = OpenRouterClient(
            api_key="sk", model_class="low",
            _client_factory=lambda **_: None,
        )
        c._async_http = _FakeAsyncClient()

        events = [e async for e in c.stream_chat(messages=[{"role":"user","content":"hi"}], max_tokens=20)]
        types = [e["type"] for e in events]
        assert types == ["content", "content", "usage", "done"]
        assert events[0]["delta"] + events[1]["delta"] == "hello"
        assert events[2]["cost_usd"] == 0.001

    asyncio.run(run())
