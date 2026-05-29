import pytest
from httpx import Response

from chara_convert.llm.credit_client import (
    CreditClient,
    CreditClientError,
    InsufficientCredit,
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
