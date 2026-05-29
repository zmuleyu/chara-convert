# Phase B — Python LLM Router + chara-convert API Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route AI enrichment through OpenRouter with credit-gated model class selection. The API route reads `X-User-Id`, holds credit, streams OR's SSE, then debits actual or refunds on failure.

**Architecture:** Five new modules under `chara_convert/llm/` (pricing, credit_client, openrouter, router) plus a factory edit; `apps/api/routes/ai_enrich.py` rewritten to drive the hold/debit lifecycle. OR streaming is wrapped in an async generator that re-emits SSE chunks while parsing OR's final `usage.cost` event in-flight.

**Tech Stack:** Python 3.11, FastAPI, `openai` SDK (already a dep) pointed at `openrouter.ai/api/v1`, `httpx` (FastAPI dep) for credit_client, `respx` for OR mocking in tests.

**Dependencies on Phase A:** Wire contract only. `credit_client` is exercised against a respx-mocked Worker; no live Worker required for tests.

**Working directory for bash commands:** `D:/projects/aichat_group/chara-convert/chara-convert/` (Python package root). API tests run from `D:/projects/aichat_group/chara-convert/apps/api/`.

---

## File structure (this phase)

| File | Status | Responsibility |
|---|---|---|
| `chara-convert/chara_convert/llm/pricing.py` | create | `PRICING_TABLE`, `usd_to_credit`, `credit_to_usd`, `estimate_max_credit` |
| `chara-convert/chara_convert/llm/credit_client.py` | create | Sync httpx client → Worker `/credit/*` |
| `chara-convert/chara_convert/llm/openrouter.py` | create | OR sync `LLMClient` + async `stream_chat(...)` generator |
| `chara-convert/chara_convert/llm/router.py` | create | `pick_model_class`, `build_or_payload`, model config constant |
| `chara-convert/chara_convert/llm/factory.py` | modify | precedence `mock > openrouter > anthropic > deepseek > none` |
| `chara-convert/pyproject.toml` | modify | move `openai` from `[deepseek]` extra to required dep; drop `[deepseek]` extra |
| `chara-convert/tests/llm/test_pricing.py` | create | rounding & boundary tests |
| `chara-convert/tests/llm/test_credit_client.py` | create | httpx-mocked client tests |
| `chara-convert/tests/llm/test_openrouter.py` | create | respx-mocked SSE roundtrip |
| `chara-convert/tests/llm/test_router.py` | create | `pick_model_class` truth table |
| `apps/api/routes/ai_enrich.py` | rewrite | X-User-Id middleware, hold→stream→debit/refund lifecycle |
| `apps/api/tests/test_ai_enrich.py` | extend | feature-flag (legacy/or) + hold/debit/refund paths |
| `apps/api/pyproject.toml` | modify | add `respx>=0.21` to `dev` extra |

---

## Task 1: `pricing.py` — table + converters (TDD)

**Files:**
- Create: [chara-convert/chara_convert/llm/pricing.py](../../chara-convert/chara_convert/llm/pricing.py)
- Create: [chara-convert/tests/llm/__init__.py](../../chara-convert/tests/llm/__init__.py) (empty)
- Create: [chara-convert/tests/llm/test_pricing.py](../../chara-convert/tests/llm/test_pricing.py)

- [ ] **Step 1: Write failing test**

```python
# tests/llm/test_pricing.py
import pytest

from chara_convert.llm.pricing import (
    PRICING_TABLE,
    USD_PER_CREDIT,
    credit_to_usd,
    estimate_max_credit,
    usd_to_credit,
)


def test_usd_to_credit_rounds_up_to_nearest_cent_of_credit():
    # 1 credit == $0.0001
    assert usd_to_credit(0.0001) == 1
    assert usd_to_credit(0.00015) == 2  # ceil
    assert usd_to_credit(0.0) == 0


def test_credit_to_usd_inverse():
    assert credit_to_usd(10000) == pytest.approx(1.0)
    assert credit_to_usd(0) == 0.0


def test_pricing_table_invariant_primary_eq_first_fallback():
    """Spec invariant: every MODEL_BY_CLASS entry has primary == fallback[0].
    The pricing module holds the per-model USD table — assert it covers every
    primary + fallback model from the spec.
    """
    required = {
        "deepseek/deepseek-chat", "moonshotai/kimi-k2",
        "anthropic/claude-3.5-sonnet", "openai/gpt-4o",
    }
    covered: set[str] = set()
    for cls_table in PRICING_TABLE.values():
        covered.update(k for k in cls_table.keys() if k != "worst_case")
    assert required.issubset(covered)


def test_estimate_max_credit_uses_worst_case_for_hold_sizing():
    # high.worst_case = {input: 3.00, output: 15.00} per spec
    # 1000 input + 800 output → (1000*3 + 800*15) / 1e6 USD = 0.015 USD = 150 credit
    n = estimate_max_credit(prompt_tokens=1000, max_tokens=800, model_class="high")
    assert n == 150


def test_usd_per_credit_constant():
    assert USD_PER_CREDIT == 0.0001
```

- [ ] **Step 2: Run — expect FAIL**

```
cd D:/projects/aichat_group/chara-convert/chara-convert
pytest tests/llm/test_pricing.py -v
```
Expected: ModuleNotFoundError on `chara_convert.llm.pricing`.

- [ ] **Step 3: Implement `pricing.py`**

```python
# chara_convert/llm/pricing.py
"""USD pricing table and credit unit conversion.

Unit: 1 credit == $0.0001 USD. All credit arithmetic is integer; USD↔credit
conversion happens at module boundaries (hold sizing, OR-reported cost ingest).
"""
from __future__ import annotations

from math import ceil
from typing import Literal

ModelClass = Literal["low", "high"]

USD_PER_CREDIT: float = 0.0001  # 1 credit

# USD per 1M tokens, seeded from OR list 2026-05-29.
# Worst-case row is used for hold sizing — must be >= every actual provider row
# in the same class.
PRICING_TABLE: dict[ModelClass, dict[str, dict[str, float]]] = {
    "low": {
        "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
        "moonshotai/kimi-k2":     {"input": 0.60, "output": 2.50},
        "worst_case":             {"input": 0.60, "output": 2.50},
    },
    "high": {
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "openai/gpt-4o":               {"input": 2.50, "output": 10.00},
        "worst_case":                  {"input": 3.00, "output": 15.00},
    },
}


def usd_to_credit(usd: float) -> int:
    if usd <= 0:
        return 0
    return ceil(usd / USD_PER_CREDIT)


def credit_to_usd(credit: int) -> float:
    return credit * USD_PER_CREDIT


def estimate_max_credit(
    *, prompt_tokens: int, max_tokens: int, model_class: ModelClass,
) -> int:
    """Worst-case credit cost for hold sizing.

    Uses the class's `worst_case` row so an OR fallback to a pricier provider
    cannot exceed the held amount.
    """
    rates = PRICING_TABLE[model_class]["worst_case"]
    usd = (prompt_tokens * rates["input"] + max_tokens * rates["output"]) / 1_000_000
    return usd_to_credit(usd)
```

- [ ] **Step 4: Run — expect PASS**

```
pytest tests/llm/test_pricing.py -v
```

- [ ] **Step 5: Commit**

```bash
git add chara-convert/chara_convert/llm/pricing.py chara-convert/tests/llm/__init__.py chara-convert/tests/llm/test_pricing.py
git commit -m "feat(llm): pricing table + credit converters + hold-size estimator"
```

---

## Task 2: `credit_client.py` — Worker HTTP client (TDD)

**Files:**
- Create: [chara-convert/chara_convert/llm/credit_client.py](../../chara-convert/chara_convert/llm/credit_client.py)
- Create: [chara-convert/tests/llm/test_credit_client.py](../../chara-convert/tests/llm/test_credit_client.py)

The Python API runs on Fly (sync FastAPI), the Worker on CF. Each request makes 2 cheap HTTPS calls (hold + debit/refund). Use `httpx.Client` (sync) — keeps API route logic flat and matches FastAPI's existing dep.

- [ ] **Step 1: Write failing tests**

```python
# tests/llm/test_credit_client.py
import pytest
from httpx import Response

from chara_convert.llm.credit_client import (
    CreditClient,
    InsufficientCredit,
    CreditClientError,
)


@pytest.fixture
def base_url() -> str:
    return "https://billing.example.test"


def _transport(handler):
    import httpx
    return httpx.MockTransport(handler)


def test_hold_returns_hold_id_and_new_balance(base_url):
    def handler(req):
        assert req.url.path == "/api/billing/credit/hold"
        assert req.headers["x-user-id"] == "u-1"
        assert req.headers["content-type"] == "application/json"
        return Response(200, json={"holdId": "h_abc", "newBalance": 700})
    c = CreditClient(base_url, transport=_transport(handler))
    out = c.hold(user_id="u-1", amount=300)
    assert out == {"holdId": "h_abc", "newBalance": 700}


def test_hold_402_raises_insufficient_credit(base_url):
    def handler(req):
        return Response(402, json={"code": "insufficient_credit", "message": "balance < amount"})
    c = CreditClient(base_url, transport=_transport(handler))
    with pytest.raises(InsufficientCredit):
        c.hold(user_id="u-1", amount=99999)


def test_debit_happy(base_url):
    def handler(req):
        assert req.url.path == "/api/billing/credit/debit"
        return Response(200, json={"newBalance": 425})
    c = CreditClient(base_url, transport=_transport(handler))
    assert c.debit(user_id="u-1", hold_id="h_x", actual_amount=75) == {"newBalance": 425}


def test_refund_swallows_409_returns_none(base_url):
    """409 hold_already_settled on refund means the debit raced ahead — not an error."""
    def handler(req):
        return Response(409, json={"code": "hold_already_settled", "message": "x"})
    c = CreditClient(base_url, transport=_transport(handler))
    assert c.refund(user_id="u-1", hold_id="h_x") is None


def test_balance_get(base_url):
    def handler(req):
        assert req.method == "GET"
        assert req.url.path == "/api/billing/credit/balance"
        return Response(200, json={"balance": 1234, "held": 56})
    c = CreditClient(base_url, transport=_transport(handler))
    assert c.balance(user_id="u-1") == {"balance": 1234, "held": 56}


def test_unknown_status_raises_generic(base_url):
    def handler(req):
        return Response(500, text="boom")
    c = CreditClient(base_url, transport=_transport(handler))
    with pytest.raises(CreditClientError):
        c.hold(user_id="u-1", amount=10)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```python
# chara_convert/llm/credit_client.py
"""Sync HTTP client to billing Worker /credit/* endpoints.

httpx.Client is reused across requests (connection pooling). Constructor
optionally accepts a custom transport for tests (MockTransport).
"""
from __future__ import annotations

from typing import Any

import httpx


class CreditClientError(RuntimeError):
    """Catch-all for unexpected Worker responses."""


class InsufficientCredit(RuntimeError):
    """Raised when the Worker rejects hold with 402."""


class CreditClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"content-type": "application/json"},
        )

    def _headers(self, user_id: str) -> dict[str, str]:
        return {"X-User-Id": user_id}

    def balance(self, *, user_id: str) -> dict[str, int]:
        r = self._client.get("/api/billing/credit/balance", headers=self._headers(user_id))
        if r.status_code != 200:
            raise CreditClientError(f"balance: {r.status_code} {r.text}")
        return r.json()

    def hold(self, *, user_id: str, amount: int) -> dict[str, Any]:
        r = self._client.post(
            "/api/billing/credit/hold",
            headers=self._headers(user_id),
            json={"amount": amount},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 402:
            raise InsufficientCredit()
        raise CreditClientError(f"hold: {r.status_code} {r.text}")

    def debit(self, *, user_id: str, hold_id: str, actual_amount: int) -> dict[str, Any]:
        r = self._client.post(
            "/api/billing/credit/debit",
            headers=self._headers(user_id),
            json={"holdId": hold_id, "actualAmount": actual_amount},
        )
        if r.status_code != 200:
            raise CreditClientError(f"debit: {r.status_code} {r.text}")
        return r.json()

    def refund(self, *, user_id: str, hold_id: str) -> dict[str, Any] | None:
        r = self._client.post(
            "/api/billing/credit/refund",
            headers=self._headers(user_id),
            json={"holdId": hold_id},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 409:
            # Already settled — debit won the race; nothing to undo.
            return None
        raise CreditClientError(f"refund: {r.status_code} {r.text}")

    def close(self) -> None:
        self._client.close()
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add chara-convert/chara_convert/llm/credit_client.py chara-convert/tests/llm/test_credit_client.py
git commit -m "feat(llm): sync HTTP credit_client with InsufficientCredit + 409-tolerant refund"
```

---

## Task 3: `openrouter.py` — sync LLMClient (TDD)

**Files:**
- Create: [chara-convert/chara_convert/llm/openrouter.py](../../chara-convert/chara_convert/llm/openrouter.py)
- Create: [chara-convert/tests/llm/test_openrouter.py](../../chara-convert/tests/llm/test_openrouter.py)

OR is OpenAI-compatible at `https://openrouter.ai/api/v1`. The sync path (`complete()`) is used by CLI/factory consumers; the async streaming path lands in Task 4.

- [ ] **Step 1: Write failing sync test**

```python
# tests/llm/test_openrouter.py
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
        self.chat = type("ns", (), {"completions": self})()  # so .chat.completions.create resolves

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


def test_missing_api_key_raises():
    import pytest
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(api_key=None, model_class="low")
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Minimal sync implementation**

```python
# chara_convert/llm/openrouter.py
"""OpenRouter client.

The OpenAI Python SDK speaks OR's API verbatim at base_url=https://openrouter.ai/api/v1.
The class exposes two interfaces:

- `complete(prompt, ...) -> str` (LLMClient contract). Used by CLI / dev paths.
- `stream_chat(messages, ...)` async generator (added in Task 4). Used by API route.

Model selection is *eager* at construction time — the class is bound to one
model_class ("low" | "high") and the OR fallback chain lives in router.MODEL_BY_CLASS.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Literal

from chara_convert.llm.base import LLMClient

ModelClass = Literal["low", "high"]

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# Mirrors spec §Model config (frozen). primary == fallback[0] is invariant.
MODEL_BY_CLASS: dict[ModelClass, dict[str, Any]] = {
    "low": {
        "primary": "deepseek/deepseek-chat",
        "fallback": ["deepseek/deepseek-chat", "moonshotai/kimi-k2"],
    },
    "high": {
        "primary": "anthropic/claude-3.5-sonnet",
        "fallback": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
    },
}


def _default_factory(**kwargs: Any) -> Any:
    import openai  # required dep
    return openai.OpenAI(**kwargs)


class OpenRouterClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_class: ModelClass = "low",
        base_url: str | None = None,
        _client_factory: Callable[..., Any] = _default_factory,
    ) -> None:
        resolved = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not resolved:
            raise ValueError("OPENROUTER_API_KEY is not set and no api_key was passed.")
        self._model_class: ModelClass = model_class
        self._cfg = MODEL_BY_CLASS[model_class]
        self._client = _client_factory(
            api_key=resolved,
            base_url=base_url or DEFAULT_BASE_URL,
        )

    @property
    def model_class(self) -> ModelClass:
        return self._model_class

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        resp = self._client.chat.completions.create(
            model=self._cfg["primary"],
            models=self._cfg["fallback"],
            extra_body={"provider": {"sort": "price", "allow_fallbacks": True}},
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        return getattr(choices[0].message, "content", "") or ""
```

> Note: `models`, `provider` are OR-specific extensions. The OpenAI SDK passes top-level kwargs through to the body. If your installed `openai` SDK rejects `models` at the typed surface, switch the offending kwargs into `extra_body` instead.

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add chara-convert/chara_convert/llm/openrouter.py chara-convert/tests/llm/test_openrouter.py
git commit -m "feat(llm): OpenRouterClient sync complete() with class-bound model + OR extras"
```

---

## Task 4: `openrouter.py` — async `stream_chat()` (TDD)

**Files:**
- Modify: [chara-convert/chara_convert/llm/openrouter.py](../../chara-convert/chara_convert/llm/openrouter.py)
- Modify: [chara-convert/tests/llm/test_openrouter.py](../../chara-convert/tests/llm/test_openrouter.py)

Yields parsed event objects so the API route can both forward content and pluck the final `usage.cost`:

```python
{"type": "content", "delta": "hello"}     # streamed token chunks
{"type": "usage",   "cost_usd": 0.0042}   # OR's final usage event (when present)
{"type": "done"}                          # OR's "[DONE]" sentinel
```

- [ ] **Step 1: Append failing test**

```python
import asyncio
from chara_convert.llm.openrouter import OpenRouterClient, parse_or_sse_line


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
        async def _aiter():
            chunks = [
                b'data: {"choices":[{"delta":{"content":"hel"}}]}\n',
                b'data: {"choices":[{"delta":{"content":"lo"}}]}\n',
                b'data: {"choices":[],"usage":{"cost":0.001}}\n',
                b'data: [DONE]\n',
            ]
            for ch in chunks:
                yield ch

        class _FakeStream:
            def __init__(self):
                self.response = type("r", (), {"aiter_bytes": _aiter})()
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False

        class _FakeAsyncClient:
            def stream(self, *a, **k): return _FakeStream()
            async def aclose(self): pass

        c = OpenRouterClient(
            api_key="sk", model_class="low",
            _client_factory=lambda **_: None,  # unused for stream path
        )
        c._async_http = _FakeAsyncClient()  # injection point

        events = [e async for e in c.stream_chat(messages=[{"role":"user","content":"hi"}], max_tokens=20)]
        types = [e["type"] for e in events]
        assert types == ["content", "content", "usage", "done"]
        assert events[0]["delta"] + events[1]["delta"] == "hello"
        assert events[2]["cost_usd"] == 0.001

    asyncio.run(run())
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement streaming**

Append to `openrouter.py`:

```python
import json
from collections.abc import AsyncGenerator

import httpx


def parse_or_sse_line(raw: bytes) -> dict[str, Any] | None:
    """Convert one OR SSE line to our internal event shape, or None for non-data."""
    if not raw.startswith(b"data:"):
        return None
    payload = raw[len(b"data:"):].strip()
    if not payload:
        return None
    if payload == b"[DONE]":
        return {"type": "done"}
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return None
    usage = obj.get("usage") or {}
    if isinstance(usage, dict) and "cost" in usage:
        return {"type": "usage", "cost_usd": float(usage["cost"])}
    choices = obj.get("choices") or []
    if choices:
        delta = (choices[0].get("delta") or {}).get("content")
        if delta is not None:
            return {"type": "content", "delta": delta}
    return None


# Patch OpenRouterClient: add stream_chat and lazy async client.

def _ensure_async_http(self: "OpenRouterClient") -> httpx.AsyncClient:
    if getattr(self, "_async_http", None) is None:
        self._async_http = httpx.AsyncClient(
            base_url=DEFAULT_BASE_URL,
            headers={
                "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY') or ''}",
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    return self._async_http


async def _stream_chat(
    self: "OpenRouterClient",
    *,
    messages: list[dict[str, str]],
    max_tokens: int = 800,
    temperature: float = 0.7,
) -> AsyncGenerator[dict[str, Any], None]:
    http = _ensure_async_http(self)
    payload = {
        "model": self._cfg["primary"],
        "models": self._cfg["fallback"],
        "provider": {"sort": "price", "allow_fallbacks": True},
        "messages": messages,
        "stream": True,
        "usage": {"include": True},
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    async with http.stream("POST", "/chat/completions", json=payload) as stream:
        buf = b""
        async for chunk in stream.response.aiter_bytes():
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                ev = parse_or_sse_line(line)
                if ev is not None:
                    yield ev
        if buf:
            ev = parse_or_sse_line(buf)
            if ev is not None:
                yield ev


OpenRouterClient.stream_chat = _stream_chat  # type: ignore[assignment]
OpenRouterClient._async_http = None  # type: ignore[assignment]
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add chara-convert/chara_convert/llm/openrouter.py chara-convert/tests/llm/test_openrouter.py
git commit -m "feat(llm): OR async stream_chat() yielding content/usage/done events"
```

---

## Task 5: `router.py` — model class selection (TDD)

**Files:**
- Create: [chara-convert/chara_convert/llm/router.py](../../chara-convert/chara_convert/llm/router.py)
- Create: [chara-convert/tests/llm/test_router.py](../../chara-convert/tests/llm/test_router.py)

- [ ] **Step 1: Write failing tests**

```python
# tests/llm/test_router.py
import pytest

from chara_convert.llm.router import (
    InsufficientCreditForAnyClass,
    pick_model_class,
    plan_request,
)


@pytest.mark.parametrize("balance,low,high,expected", [
    (10000, 150, 50, "high"),
    (100,   50, 150, "low"),
    (50,    50, 150, "low"),
    (49,    50, 150, None),  # raises
])
def test_pick_model_class(balance, low, high, expected):
    if expected is None:
        with pytest.raises(InsufficientCreditForAnyClass):
            pick_model_class(balance=balance, est_low=low, est_high=high)
    else:
        assert pick_model_class(balance=balance, est_low=low, est_high=high) == expected


def test_plan_request_returns_chosen_class_and_hold_amount():
    plan = plan_request(
        balance=1000,
        prompt_tokens=500, max_tokens=400,
    )
    # high hold ~ ceil((500*3 + 400*15)/1e6 / 0.0001) = ceil(0.0090/0.0001) = 90
    # low  hold ~ ceil((500*0.60 + 400*2.50)/1e6 / 0.0001) = ceil(0.0013/0.0001) = 13
    assert plan["model_class"] == "high"
    assert plan["hold_amount"] == 90


def test_plan_request_falls_back_to_low_when_balance_only_covers_low():
    plan = plan_request(balance=50, prompt_tokens=500, max_tokens=400)
    assert plan["model_class"] == "low"
    assert plan["hold_amount"] == 13
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```python
# chara_convert/llm/router.py
"""Model-class selection and request planning.

The router is the pure-logic layer between the API route and the OR client.
It decides:
  1. Which model class the user can afford (high > low > 402).
  2. The hold amount (worst-case per class).

It does not touch HTTP, credit, or the OR client directly.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from chara_convert.llm.pricing import estimate_max_credit

ModelClass = Literal["low", "high"]


class InsufficientCreditForAnyClass(RuntimeError):
    """Balance < estimated_low. Surface as 402 at the route boundary."""


class RequestPlan(TypedDict):
    model_class: ModelClass
    hold_amount: int


def pick_model_class(*, balance: int, est_low: int, est_high: int) -> ModelClass:
    if balance >= est_high:
        return "high"
    if balance >= est_low:
        return "low"
    raise InsufficientCreditForAnyClass()


def plan_request(*, balance: int, prompt_tokens: int, max_tokens: int) -> RequestPlan:
    est_low  = estimate_max_credit(prompt_tokens=prompt_tokens, max_tokens=max_tokens, model_class="low")
    est_high = estimate_max_credit(prompt_tokens=prompt_tokens, max_tokens=max_tokens, model_class="high")
    cls = pick_model_class(balance=balance, est_low=est_low, est_high=est_high)
    hold_amount = est_high if cls == "high" else est_low
    return {"model_class": cls, "hold_amount": hold_amount}
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add chara-convert/chara_convert/llm/router.py chara-convert/tests/llm/test_router.py
git commit -m "feat(llm): router.plan_request + pick_model_class with affordability gates"
```

---

## Task 6: `factory.py` — add openrouter to precedence

**Files:**
- Modify: [chara-convert/chara_convert/llm/factory.py](../../chara-convert/chara_convert/llm/factory.py)
- Create: [chara-convert/tests/llm/test_factory_openrouter.py](../../chara-convert/tests/llm/test_factory_openrouter.py)

Precedence: `mock > openrouter > anthropic > deepseek > none`. Anthropic/DeepSeek retained but moved behind OR so prod (which sets only `OPENROUTER_API_KEY`) hits OR.

- [ ] **Step 1: Write failing test**

```python
# tests/llm/test_factory_openrouter.py
def test_openrouter_takes_precedence_over_anthropic(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    # Patch openai.OpenAI so OpenRouterClient construction succeeds without network.
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **_: object())

    from chara_convert.llm.factory import build_ai_client_or_none
    client, status = build_ai_client_or_none()
    assert status == "openrouter"
    from chara_convert.llm.openrouter import OpenRouterClient
    assert isinstance(client, OpenRouterClient)


def test_mock_still_wins_over_openrouter(monkeypatch):
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    from chara_convert.llm.factory import build_ai_client_or_none
    _, status = build_ai_client_or_none()
    assert status == "mock"


def test_legacy_anthropic_still_works_when_no_or_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **_: object())
    from chara_convert.llm.factory import build_ai_client_or_none
    _, status = build_ai_client_or_none()
    assert status == "anthropic"
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Edit `factory.py`** — insert OR branch between mock and anthropic

```python
# After the mock branch, before the anthropic branch:
    if os.environ.get("OPENROUTER_API_KEY"):
        from chara_convert.llm.openrouter import OpenRouterClient

        # The default class for CLI/dev consumers is "low" — cheaper smoke runs.
        # API route uses router.plan_request() and bypasses the factory.
        model_class = os.environ.get("CHARA_CONVERT_OR_CLASS", "low")
        return OpenRouterClient(model_class=model_class), "openrouter"  # type: ignore[arg-type]
```

Also update the module docstring's precedence list to include `openrouter`.

- [ ] **Step 4: Run — expect PASS** (all 3 tests).

- [ ] **Step 5: Commit**

```bash
git add chara-convert/chara_convert/llm/factory.py chara-convert/tests/llm/test_factory_openrouter.py
git commit -m "feat(llm): factory precedence mock > openrouter > anthropic > deepseek"
```

---

## Task 7: `ai_enrich.py` rewrite — credit lifecycle + SSE forward

**Files:**
- Modify: [apps/api/routes/ai_enrich.py](../../apps/api/routes/ai_enrich.py)
- Modify: [apps/api/tests/test_ai_enrich.py](../../apps/api/tests/test_ai_enrich.py)
- Modify: [apps/api/pyproject.toml](../../apps/api/pyproject.toml) (add `respx`)

Request lifecycle (spec §Credit accounting):
1. Require `X-User-Id` header (400 if missing).
2. Build prompt; estimate `prompt_tokens` (tiktoken-style rough: `len(prompt)//4`).
3. `credit_client.balance()` → `router.plan_request(...)` → hold the amount; 402 on InsufficientCredit.
4. `or.stream_chat()` async; forward each `content` event as SSE; capture `usage.cost` if seen.
5. On normal `done`: `debit(actual)` where actual = `usd_to_credit(cost)` or local estimate fallback.
6. On `Exception` / client disconnect: `refund(hold_id)` (best-effort).
7. Feature flag `LLM_ROUTER_MODE`: `legacy` (current sync behavior) | `or` (new path).

- [ ] **Step 1: Add respx to API dev extras**

`apps/api/pyproject.toml`:
```toml
dev = ["pytest>=8", "httpx>=0.27", "pytest-asyncio>=0.23", "respx>=0.21"]
```

Install:
```
cd apps/api && pip install -e ".[dev]"
```

- [ ] **Step 2: Write failing tests for the OR path**

Append to `apps/api/tests/test_ai_enrich.py`:

```python
import pytest
import respx
from httpx import Response


@pytest.fixture
def or_mode(monkeypatch):
    monkeypatch.setenv("LLM_ROUTER_MODE", "or")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("BILLING_WORKER_URL", "https://billing.example.test")
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    yield


@respx.mock
def test_or_path_402_when_balance_insufficient(client, or_mode):
    respx.get("https://billing.example.test/api/billing/credit/balance").mock(
        return_value=Response(200, json={"balance": 0, "held": 0}),
    )
    res = client.post(
        "/api/ai/enrich",
        headers={"X-User-Id": "u-1"},
        json={"card": {"name": "x", "description": "y"}, "field": "personality"},
    )
    assert res.status_code == 402
    assert res.json()["code"] == "insufficient_credit"


def test_or_path_400_when_missing_user_header(client, or_mode):
    res = client.post(
        "/api/ai/enrich",
        json={"card": {"name": "x"}, "field": "personality"},
    )
    assert res.status_code == 400


@respx.mock
def test_or_path_happy_streams_and_debits(client, or_mode, monkeypatch):
    # Fake credit Worker
    respx.get("https://billing.example.test/api/billing/credit/balance").mock(
        return_value=Response(200, json={"balance": 5000, "held": 0}),
    )
    respx.post("https://billing.example.test/api/billing/credit/hold").mock(
        return_value=Response(200, json={"holdId": "h_test", "newBalance": 4910}),
    )
    debit_route = respx.post("https://billing.example.test/api/billing/credit/debit").mock(
        return_value=Response(200, json={"newBalance": 4995}),
    )

    # Fake OR streaming: replace OpenRouterClient.stream_chat with a canned async gen
    async def fake_stream(self, *, messages, max_tokens=800, temperature=0.7):
        yield {"type": "content", "delta": "calm "}
        yield {"type": "content", "delta": "and observant."}
        yield {"type": "usage", "cost_usd": 0.0005}
        yield {"type": "done"}

    from chara_convert.llm import openrouter
    monkeypatch.setattr(openrouter.OpenRouterClient, "stream_chat", fake_stream)

    with client.stream(
        "POST", "/api/ai/enrich",
        headers={"X-User-Id": "u-1"},
        json={"card": {"name": "Aerin", "description": "wandering mage"}, "field": "personality"},
    ) as res:
        assert res.status_code == 200
        chunks = [line for line in res.iter_lines() if line.startswith("data:")]

    text = "".join(c.removeprefix("data:").strip() for c in chunks if not c.startswith("data: [DONE]"))
    assert "calm" in text and "observant" in text

    # cost 0.0005 USD → 5 credit
    debit_call = debit_route.calls.last
    body = debit_call.request.content.decode()
    assert '"actualAmount": 5' in body or '"actualAmount":5' in body
    assert '"holdId": "h_test"' in body or '"holdId":"h_test"' in body


@respx.mock
def test_or_path_refunds_on_stream_error(client, or_mode, monkeypatch):
    respx.get("https://billing.example.test/api/billing/credit/balance").mock(
        return_value=Response(200, json={"balance": 5000, "held": 0}),
    )
    respx.post("https://billing.example.test/api/billing/credit/hold").mock(
        return_value=Response(200, json={"holdId": "h_err", "newBalance": 4910}),
    )
    refund_route = respx.post("https://billing.example.test/api/billing/credit/refund").mock(
        return_value=Response(200, json={"newBalance": 5000}),
    )

    async def boom_stream(self, *, messages, max_tokens=800, temperature=0.7):
        yield {"type": "content", "delta": "calm"}
        raise RuntimeError("upstream broke")

    from chara_convert.llm import openrouter
    monkeypatch.setattr(openrouter.OpenRouterClient, "stream_chat", boom_stream)

    with client.stream(
        "POST", "/api/ai/enrich",
        headers={"X-User-Id": "u-1"},
        json={"card": {"name": "x", "description": "y"}, "field": "personality"},
    ) as res:
        # Headers already flushed → status 200; error surfaces in SSE error frame
        list(res.iter_lines())

    assert refund_route.called


@respx.mock
def test_legacy_mode_still_works_without_x_user_id(client, monkeypatch):
    monkeypatch.setenv("LLM_ROUTER_MODE", "legacy")
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "calm")
    res = client.post(
        "/api/ai/enrich",
        json={"card": {"name": "x", "description": "y"}, "field": "personality"},
    )
    assert res.status_code == 200  # legacy path unchanged
```

- [ ] **Step 3: Run — expect FAIL** (route not yet OR-aware).

- [ ] **Step 4: Rewrite `apps/api/routes/ai_enrich.py`**

```python
from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from dataclasses import fields
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from chara_convert.ai.enrich import build_field_prompt
from chara_convert.llm.credit_client import CreditClient, CreditClientError, InsufficientCredit
from chara_convert.llm.factory import build_ai_client_or_none
from chara_convert.llm.mock import MockLLMClient
from chara_convert.llm.openrouter import OpenRouterClient
from chara_convert.llm.pricing import usd_to_credit
from chara_convert.llm.router import InsufficientCreditForAnyClass, plan_request
from chara_convert.normalizer import NormalizedCard

router = APIRouter()

ALLOWED_FIELDS: set[str] = {
    "personality", "scenario", "first_message",
    "mes_example", "description", "appearance",
}


class EnrichRequest(BaseModel):
    card: dict
    field: Literal[
        "personality", "scenario", "first_message",
        "mes_example", "description", "appearance",
    ]


def _normalized_card(card_in: dict) -> NormalizedCard:
    known = {f.name for f in fields(NormalizedCard)}
    safe = {k: v for k, v in card_in.items() if k in known}
    if "first_message" in card_in and "first_mes" not in safe:
        safe["first_mes"] = card_in["first_message"]
    return NormalizedCard(**safe)


def _legacy_client():
    mock = os.environ.get("CHARA_CONVERT_AI_MOCK")
    if mock:
        return MockLLMClient(responses=mock)
    client, _ = build_ai_client_or_none()
    return client


async def _legacy_stream(prompt: str) -> AsyncGenerator[bytes, None]:
    client = _legacy_client()
    if client is None:
        yield b"data: (no LLM client available)\n\n"
        return
    text = client.complete(prompt, max_tokens=400, temperature=0.7)
    for chunk in text.split(" "):
        yield f"data: {chunk} \n\n".encode()


def _est_prompt_tokens(prompt: str) -> int:
    # Rough heuristic; OR's usage event will give us the actual amount.
    return max(1, len(prompt) // 4)


async def _or_stream(
    *,
    user_id: str,
    prompt: str,
    max_tokens: int,
    plan: dict,
    cc: CreditClient,
) -> AsyncGenerator[bytes, None]:
    """Caller is responsible for (1) the pre-stream balance/plan_request gate
    so 4xx envelopes go out before the SSE headers are flushed and (2) passing
    in the resolved CreditClient + plan."""
    or_client = OpenRouterClient(model_class=plan["model_class"])
    held = cc.hold(user_id=user_id, amount=plan["hold_amount"])
    hold_id = held["holdId"]

    actual_cost_usd: float | None = None
    settled = False
    try:
        async for ev in or_client.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        ):
            if ev["type"] == "content":
                yield f"data: {ev['delta']}\n\n".encode()
            elif ev["type"] == "usage":
                actual_cost_usd = ev["cost_usd"]
            elif ev["type"] == "done":
                yield b"data: [DONE]\n\n"
                break

        if actual_cost_usd is not None:
            actual_credit = usd_to_credit(actual_cost_usd)
        else:
            # cost missing — bill the held estimate, emit metric
            # Metric emission deferred to observability layer (out of plan B scope).
            actual_credit = plan["hold_amount"]
        cc.debit(user_id=user_id, hold_id=hold_id, actual_amount=actual_credit)
        settled = True
    except Exception as e:
        # Emit SSE error frame, then let `finally` refund. Do NOT re-raise — that
        # would close the stream abruptly mid-frame on FastAPI.
        yield (
            "data: " + json.dumps({"event": "error", "code": "or_unavailable", "message": str(e)[:120]})
            + "\n\n"
        ).encode()
    finally:
        if not settled:
            try:
                cc.refund(user_id=user_id, hold_id=hold_id)
            except CreditClientError:
                pass  # orphan-hold cron will pick it up


@router.post("/ai/enrich")
async def enrich(
    body: EnrichRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if body.field not in ALLOWED_FIELDS:
        raise HTTPException(status_code=422, detail="unsupported field")
    card = _normalized_card(body.card)
    prompt = build_field_prompt(card, body.field)
    max_tokens = 400

    mode = os.environ.get("LLM_ROUTER_MODE", "legacy")
    if mode != "or":
        return StreamingResponse(_legacy_stream(prompt), media_type="text/event-stream")

    # OR path: validate user header + balance *before* opening the stream so we can
    # return 4xx with a JSON envelope rather than an error inside an SSE body.
    if not x_user_id:
        return JSONResponse(
            status_code=400,
            content={"code": "missing_user_id", "message": "X-User-Id header is required"},
        )
    billing_url = os.environ["BILLING_WORKER_URL"]
    cc = CreditClient(billing_url)
    try:
        bal = cc.balance(user_id=x_user_id)
        plan = plan_request(
            balance=bal["balance"],
            prompt_tokens=_est_prompt_tokens(prompt),
            max_tokens=max_tokens,
        )
    except InsufficientCreditForAnyClass:
        return JSONResponse(
            status_code=402,
            content={"code": "insufficient_credit", "message": "balance below low-class estimate"},
        )
    except InsufficientCredit:
        return JSONResponse(
            status_code=402,
            content={"code": "insufficient_credit", "message": "balance < amount"},
        )

    return StreamingResponse(
        _or_stream(
            user_id=x_user_id, prompt=prompt, max_tokens=max_tokens, plan=plan, cc=cc,
        ),
        media_type="text/event-stream",
    )
```

- [ ] **Step 5: Run — expect PASS** (all old + new tests)

```
cd apps/api && pytest tests/test_ai_enrich.py -v
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/routes/ai_enrich.py apps/api/tests/test_ai_enrich.py apps/api/pyproject.toml
git commit -m "feat(api): ai_enrich OR path with X-User-Id + hold/debit/refund lifecycle"
```

---

## Task 8: `pyproject.toml` cleanup

**Files:**
- Modify: [chara-convert/pyproject.toml](../../chara-convert/pyproject.toml)

Move `openai>=1.0.0` from the `[deepseek]` optional extra to the required `dependencies` list (OR client uses it). Delete the now-empty `[deepseek]` extra. Keep `anthropic` in `[ai]` extra (legacy path retention).

- [ ] **Step 1: Edit `pyproject.toml`**

```toml
dependencies = [
    "click>=8.1.0",
    "openai>=1.0.0",  # OR client uses OpenAI-compatible SDK
    "httpx>=0.27.0",  # credit_client + OR async streaming
]

[project.optional-dependencies]
ai = [
    "anthropic>=0.40.0",
]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
    "respx>=0.21.0",
    "pytest-asyncio>=0.23.0",
]
```

- [ ] **Step 2: Reinstall + re-run full pytest**

```
cd chara-convert && pip install -e ".[dev]"
pytest tests/llm/ -v
cd ../apps/api && pip install -e ".[dev]"
pytest tests/test_ai_enrich.py -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add chara-convert/pyproject.toml
git commit -m "chore(deps): promote openai+httpx to required, drop [deepseek] extra"
```

---

## Task 9: End-to-end mocked test — hold → stream → debit conservation

**Files:**
- Create: [apps/api/tests/test_ai_enrich_lifecycle.py](../../apps/api/tests/test_ai_enrich_lifecycle.py)

One test that verifies the full hold→debit accounting math without touching real OR or real Worker. Backstop against regressions in the lifecycle wiring.

- [ ] **Step 1: Write test**

```python
import respx
from httpx import Response


@respx.mock
def test_full_lifecycle_hold_then_debit_amount_matches_or_cost(client, monkeypatch):
    monkeypatch.setenv("LLM_ROUTER_MODE", "or")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("BILLING_WORKER_URL", "https://billing.example.test")

    respx.get("https://billing.example.test/api/billing/credit/balance").mock(
        return_value=Response(200, json={"balance": 10000, "held": 0}),
    )
    hold_route = respx.post("https://billing.example.test/api/billing/credit/hold").mock(
        return_value=Response(200, json={"holdId": "h_full", "newBalance": 9000}),
    )
    debit_route = respx.post("https://billing.example.test/api/billing/credit/debit").mock(
        return_value=Response(200, json={"newBalance": 9988}),
    )

    async def fake_stream(self, *, messages, max_tokens=800, temperature=0.7):
        yield {"type": "content", "delta": "x"}
        yield {"type": "usage", "cost_usd": 0.0012}  # 12 credit
        yield {"type": "done"}

    from chara_convert.llm import openrouter
    monkeypatch.setattr(openrouter.OpenRouterClient, "stream_chat", fake_stream)

    with client.stream(
        "POST", "/api/ai/enrich",
        headers={"X-User-Id": "u-z"},
        json={"card": {"name": "x", "description": "y"}, "field": "personality"},
    ) as res:
        for _ in res.iter_lines():
            pass

    hold_body = hold_route.calls.last.request.content.decode()
    debit_body = debit_route.calls.last.request.content.decode()
    # hold ≥ debit (worst-case ≥ actual)
    import json as _json
    h_amount = _json.loads(hold_body)["amount"]
    d_amount = _json.loads(debit_body)["actualAmount"]
    assert h_amount >= d_amount == 12
```

- [ ] **Step 2: Run — expect PASS** (no implementation change).

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/test_ai_enrich_lifecycle.py
git commit -m "test(api): lifecycle conservation — hold ≥ debit == OR-reported cost"
```

---

## Task 10: 1× real OR CI smoke (budget cap $0.01)

**Files:**
- Create: [chara-convert/tests/llm/test_openrouter_live.py](../../chara-convert/tests/llm/test_openrouter_live.py)
- Modify: [chara-convert/pyproject.toml](../../chara-convert/pyproject.toml) (add `live_smoke` pytest marker)

Skipped by default. Runs in CI only when `RUN_OR_SMOKE=1` and `OPENROUTER_API_KEY` is set. Capped at `max_tokens=20`.

- [ ] **Step 1: Register pytest marker**

Append to `chara-convert/pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["live_smoke: hits live OR API; gated by RUN_OR_SMOKE=1"]
```

- [ ] **Step 2: Write test**

```python
# tests/llm/test_openrouter_live.py
import os

import pytest

pytestmark = pytest.mark.live_smoke


@pytest.mark.skipif(os.environ.get("RUN_OR_SMOKE") != "1", reason="set RUN_OR_SMOKE=1 to run")
def test_real_or_low_class_returns_text_within_budget():
    from chara_convert.llm.openrouter import OpenRouterClient
    c = OpenRouterClient(model_class="low")
    out = c.complete("Say hello in three words.", max_tokens=20, temperature=0.1)
    assert isinstance(out, str)
    assert len(out) > 0
```

> CI invocation: `RUN_OR_SMOKE=1 OPENROUTER_API_KEY=$OR_KEY pytest -m live_smoke -v`.
> Cost: `deepseek/deepseek-chat` at 20 output tokens ≤ $0.000006. Well under the $0.01 budget cap.

- [ ] **Step 3: Run locally** (only if you have an OR key)

```
RUN_OR_SMOKE=1 OPENROUTER_API_KEY=$OR_KEY pytest -m live_smoke -v
```
Expected: PASS, ≤2s runtime.

- [ ] **Step 4: Commit**

```bash
git add chara-convert/tests/llm/test_openrouter_live.py chara-convert/pyproject.toml
git commit -m "test(llm): live OR smoke gated by RUN_OR_SMOKE=1"
```

---

## Task 11: Drift guard — monthly pricing diff cron stub

**Files:**
- Create: [scripts/pricing_drift_check.py](../../scripts/pricing_drift_check.py)

Pulls OR's public models endpoint, compares to `PRICING_TABLE`, prints diff. Intended for a monthly cron (not wired here — scheduling lives in ops repo). Read-only; alerts via stdout exit code.

- [ ] **Step 1: Write script**

```python
#!/usr/bin/env python3
"""Compare PRICING_TABLE against OR's live model list. Exit 1 if any per-token
price drifts > 20%. Designed to run monthly; output is consumed by an external
notifier (out of scope here)."""
from __future__ import annotations

import json
import sys
import urllib.request

from chara_convert.llm.pricing import PRICING_TABLE

OR_MODELS = "https://openrouter.ai/api/v1/models"
THRESHOLD = 0.20


def main() -> int:
    req = urllib.request.Request(OR_MODELS, headers={"User-Agent": "drift-guard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — fixed URL
        data = json.load(resp)
    live: dict[str, dict[str, float]] = {}
    for m in data.get("data", []):
        slug = m.get("id")
        pricing = m.get("pricing") or {}
        if not slug:
            continue
        try:
            # OR's pricing is per-token strings → convert to per-1M float
            live[slug] = {
                "input":  float(pricing["prompt"]) * 1_000_000,
                "output": float(pricing["completion"]) * 1_000_000,
            }
        except (KeyError, TypeError, ValueError):
            continue

    drifts: list[str] = []
    for cls_table in PRICING_TABLE.values():
        for slug, rates in cls_table.items():
            if slug == "worst_case":
                continue
            seen = live.get(slug)
            if not seen:
                drifts.append(f"{slug}: missing in OR live list")
                continue
            for k in ("input", "output"):
                a, b = rates[k], seen[k]
                if a == 0:
                    continue
                if abs(a - b) / a > THRESHOLD:
                    drifts.append(f"{slug}/{k}: seed={a} live={b:.4f} drift={abs(a-b)/a:.0%}")

    if drifts:
        print("PRICING DRIFT DETECTED:")
        for d in drifts:
            print("  - " + d)
        return 1
    print("pricing table within 20% of OR live rates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke run** (requires network)

```
python scripts/pricing_drift_check.py
```
Expected: exits 0 (or 1 with diff list) within 5 seconds.

- [ ] **Step 3: Commit**

```bash
git add scripts/pricing_drift_check.py
git commit -m "feat(scripts): monthly OR pricing drift guard (20% threshold)"
```

---

## Phase B done — acceptance criteria

- ✅ `cd chara-convert && pytest tests/llm/ -v` green
- ✅ `cd apps/api && pytest tests/test_ai_enrich.py tests/test_ai_enrich_lifecycle.py -v` green
- ✅ `LLM_ROUTER_MODE=legacy` path unchanged (regression-safe behind the flag)
- ✅ `LLM_ROUTER_MODE=or` path: 400 missing-user / 402 insufficient / 200 streams + debits actual / refunds on stream error
- ✅ Drift guard script runs and returns within 5s
- ✅ All commits land on branch
- ✅ Optional: `RUN_OR_SMOKE=1 pytest -m live_smoke` green (manual; not gated in CI by default)

Hand-off to Phase C: API now exports the `or` mode behind `LLM_ROUTER_MODE` flag. Phase C deploys the Worker (from A), wires Web client polling, configures BYOK + secrets, then flips the flag in staging.

