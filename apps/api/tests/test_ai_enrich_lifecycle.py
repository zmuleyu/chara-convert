import respx
from httpx import Response


@respx.mock
def test_full_lifecycle_hold_then_debit_amount_matches_or_cost(client, monkeypatch):
    monkeypatch.setenv("LLM_ROUTER_MODE", "or")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("BILLING_WORKER_URL", "https://billing.example.test")
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)

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

    import json as _json
    hold_body = hold_route.calls.last.request.content.decode()
    debit_body = debit_route.calls.last.request.content.decode()
    h_amount = _json.loads(hold_body)["amount"]
    d_amount = _json.loads(debit_body)["actualAmount"]
    # hold >= debit (worst-case >= actual); debit matches OR-reported cost.
    assert h_amount >= d_amount == 12
