import pytest
from httpx import Response

from chara_convert.llm.credit_client import (
    BillingServiceUnavailable,
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


def _client(base_url: str, handler, **kwargs) -> CreditClient:
    # Default retries=0 in tests so we don't sleep unless the case asks.
    kwargs.setdefault("retries", 0)
    return CreditClient(base_url, transport=_transport(handler), **kwargs)


def test_hold_returns_hold_id_and_new_balance(base_url):
    def handler(req):
        assert req.url.path == "/api/billing/credit/hold"
        assert req.headers["x-user-id"] == "u-1"
        assert req.headers["content-type"] == "application/json"
        return Response(200, json={"holdId": "h_abc", "newBalance": 700})
    c = _client(base_url, handler)
    out = c.hold(user_id="u-1", amount=300)
    assert out == {"holdId": "h_abc", "newBalance": 700}


def test_hold_402_raises_insufficient_credit(base_url):
    def handler(req):
        return Response(402, json={"code": "insufficient_credit", "message": "balance < amount"})
    c = _client(base_url, handler)
    with pytest.raises(InsufficientCredit):
        c.hold(user_id="u-1", amount=99999)


def test_debit_happy(base_url):
    def handler(req):
        assert req.url.path == "/api/billing/credit/debit"
        return Response(200, json={"newBalance": 425})
    c = _client(base_url, handler)
    assert c.debit(user_id="u-1", hold_id="h_x", actual_amount=75) == {"newBalance": 425}


def test_refund_swallows_409_returns_none(base_url):
    """409 hold_already_settled on refund means the debit raced ahead — not an error."""
    def handler(req):
        return Response(409, json={"code": "hold_already_settled", "message": "x"})
    c = _client(base_url, handler)
    assert c.refund(user_id="u-1", hold_id="h_x") is None


def test_balance_get(base_url):
    def handler(req):
        assert req.method == "GET"
        assert req.url.path == "/api/billing/credit/balance"
        return Response(200, json={"balance": 1234, "held": 56})
    c = _client(base_url, handler)
    assert c.balance(user_id="u-1") == {"balance": 1234, "held": 56}


# A.1.x-M1: 5xx error handling


def test_hold_500_raises_service_unavailable_not_generic(base_url):
    """5xx on hold surfaces BillingServiceUnavailable so callers can tell
    transient failure apart from caller-error (4xx)."""
    def handler(req):
        return Response(500, json={"code": "internal_error", "message": "boom"})
    c = _client(base_url, handler)
    with pytest.raises(BillingServiceUnavailable):
        c.hold(user_id="u-1", amount=10)


def test_hold_does_not_retry_on_5xx(base_url):
    """hold is non-idempotent — a retry could create a phantom second hold.
    Verify the handler is invoked exactly once even when retries=5."""
    calls = []
    def handler(req):
        calls.append(1)
        return Response(503, json={"code": "service_unavailable", "message": "x"})
    c = _client(base_url, handler, retries=5, retry_backoff_s=0.001)
    with pytest.raises(BillingServiceUnavailable):
        c.hold(user_id="u-1", amount=10)
    assert len(calls) == 1


def test_debit_retries_on_5xx_and_eventually_succeeds(base_url):
    """debit is key-idempotent (Worker dedupes via 409) — safe to retry."""
    calls = []
    def handler(req):
        calls.append(1)
        if len(calls) < 3:
            return Response(503, json={"code": "service_unavailable", "message": "x"})
        return Response(200, json={"newBalance": 100})
    c = _client(base_url, handler, retries=2, retry_backoff_s=0.001)
    assert c.debit(user_id="u", hold_id="h", actual_amount=10) == {"newBalance": 100}
    assert len(calls) == 3


def test_debit_exhausts_retries_then_raises_service_unavailable(base_url):
    calls = []
    def handler(req):
        calls.append(1)
        return Response(500, json={"code": "internal_error", "message": "x"})
    c = _client(base_url, handler, retries=2, retry_backoff_s=0.001)
    with pytest.raises(BillingServiceUnavailable):
        c.debit(user_id="u", hold_id="h", actual_amount=10)
    assert len(calls) == 3  # initial + 2 retries


def test_refund_retries_on_5xx(base_url):
    calls = []
    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            return Response(503, json={"code": "service_unavailable", "message": "x"})
        return Response(200, json={"newBalance": 50})
    c = _client(base_url, handler, retries=2, retry_backoff_s=0.001)
    assert c.refund(user_id="u", hold_id="h") == {"newBalance": 50}
    assert len(calls) == 2


def test_balance_retries_on_5xx(base_url):
    calls = []
    def handler(req):
        calls.append(1)
        if len(calls) < 2:
            return Response(500, json={"code": "internal_error", "message": "x"})
        return Response(200, json={"balance": 1, "held": 0})
    c = _client(base_url, handler, retries=2, retry_backoff_s=0.001)
    assert c.balance(user_id="u") == {"balance": 1, "held": 0}
    assert len(calls) == 2


def test_balance_4xx_does_not_retry(base_url):
    """400/4xx is caller-error — must not retry."""
    calls = []
    def handler(req):
        calls.append(1)
        return Response(400, json={"code": "missing_user_id", "message": "x"})
    c = _client(base_url, handler, retries=5, retry_backoff_s=0.001)
    with pytest.raises(CreditClientError):
        c.balance(user_id="u")
    assert len(calls) == 1


def test_service_unavailable_is_credit_client_error_subclass():
    """Callers using `except CreditClientError` (e.g. ai_enrich refund cleanup)
    still catch BillingServiceUnavailable — backwards compatible."""
    assert issubclass(BillingServiceUnavailable, CreditClientError)


def test_5xx_without_json_body_still_raises_service_unavailable(base_url):
    def handler(req):
        return Response(500, text="plain text boom")
    c = _client(base_url, handler, retries=0)
    with pytest.raises(BillingServiceUnavailable):
        c.debit(user_id="u", hold_id="h", actual_amount=1)
