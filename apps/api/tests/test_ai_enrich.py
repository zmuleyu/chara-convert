import os

import pytest
import respx
from httpx import Response


def test_ai_enrich_mock_streams_chunks(client, monkeypatch):
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "Aerin is calm and quietly observant.")
    body = {
        "card": {"name": "Aerin", "description": "wandering mage"},
        "field": "personality",
    }
    with client.stream("POST", "/api/ai/enrich", json=body) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        chunks = [line for line in res.iter_lines() if line.startswith("data:")]
    text = "".join(c.removeprefix("data:").strip() for c in chunks)
    assert "Aerin" in text


def test_ai_enrich_422_on_unknown_field(client):
    res = client.post("/api/ai/enrich", json={"card": {}, "field": "wat"})
    assert res.status_code == 422


def test_ai_enrich_ignores_unknown_card_keys(client, monkeypatch):
    """Regression: frontend merges sourceCard + converted + overrides into the
    card dict; extra keys like 'appearance' or layer-flattened fields must not
    crash NormalizedCard construction. first_message → first_mes alias too."""
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "calm and quietly observant")
    body = {
        "card": {
            "name": "Aerin",
            "description": "wandering mage",
            "first_message": "Hello, traveler.",
            "appearance": "tall, dark hair",
            "vibes_layer": "moody",
            "ready_score": 42,
        },
        "field": "personality",
    }
    with client.stream("POST", "/api/ai/enrich", json=body) as res:
        assert res.status_code == 200
        chunks = [line for line in res.iter_lines() if line.startswith("data:")]
    text = "".join(c.removeprefix("data:").strip() for c in chunks)
    assert "calm" in text


# --- OR path (LLM_ROUTER_MODE=or) — Phase B T7 ---


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
    respx.get("https://billing.example.test/api/billing/credit/balance").mock(
        return_value=Response(200, json={"balance": 5000, "held": 0}),
    )
    respx.post("https://billing.example.test/api/billing/credit/hold").mock(
        return_value=Response(200, json={"holdId": "h_test", "newBalance": 4910}),
    )
    debit_route = respx.post("https://billing.example.test/api/billing/credit/debit").mock(
        return_value=Response(200, json={"newBalance": 4995}),
    )

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
    assert res.status_code == 200
