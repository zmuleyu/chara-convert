"""Sync HTTP client to billing Worker /credit/* endpoints.

httpx.Client is reused across requests (connection pooling). Constructor
optionally accepts a custom transport for tests (MockTransport).

Retry policy (A.1.x-M1):
  - balance / debit / refund are key-idempotent (GET or carry a holdId the
    Worker dedupes via 409 hold_already_settled), so a 5xx is safe to retry.
  - hold is NOT idempotent — a retry that lands a phantom second hold would
    over-charge the user. On 5xx hold raises BillingServiceUnavailable so the
    caller can render a "try again later" envelope.
  - 4xx responses are caller-error and never retried.

Error class hierarchy:
  CreditClientError                # catch-all for unexpected Worker responses
    └─ BillingServiceUnavailable   # 5xx after retries exhausted (or no-retry path)
  InsufficientCredit               # 402 on hold — separate signal for the UI
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class CreditClientError(RuntimeError):
    """Catch-all for unexpected Worker responses."""


class BillingServiceUnavailable(CreditClientError):
    """5xx from the Worker — DO unreachable / internal error after retries."""


class InsufficientCredit(RuntimeError):
    """Raised when the Worker rejects hold with 402."""


def _parse_code(resp: httpx.Response) -> str | None:
    try:
        body = resp.json()
    except Exception:
        return None
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, str) else None


class CreditClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
        retries: int = 2,
        retry_backoff_s: float = 0.05,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"content-type": "application/json"},
        )
        self._retries = retries
        self._retry_backoff_s = retry_backoff_s

    def _headers(self, user_id: str) -> dict[str, str]:
        return {"X-User-Id": user_id}

    def _send_idempotent(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send with retry on 5xx. Only call for endpoints whose semantics
        guarantee retry safety (balance/debit/refund)."""
        last: httpx.Response | None = None
        for attempt in range(self._retries + 1):
            r = self._client.request(method, path, headers=headers, json=json)
            if r.status_code < 500:
                return r
            last = r
            if attempt < self._retries:
                # exponential backoff: 50ms → 100ms (default)
                time.sleep(self._retry_backoff_s * (2 ** attempt))
        assert last is not None
        return last

    def balance(self, *, user_id: str) -> dict[str, int]:
        r = self._send_idempotent("GET", "/api/billing/credit/balance", headers=self._headers(user_id))
        if r.status_code == 200:
            return r.json()
        if r.status_code >= 500:
            raise BillingServiceUnavailable(f"balance: {r.status_code} {_parse_code(r)}")
        raise CreditClientError(f"balance: {r.status_code} {r.text}")

    def hold(self, *, user_id: str, amount: int) -> dict[str, Any]:
        # Not idempotent — single shot, no retry. If the response is 5xx we
        # don't know if the hold landed; surface BillingServiceUnavailable so
        # the caller can show a transient-failure envelope and the orphan-hold
        # cron will refund any actually-created hold.
        r = self._client.post(
            "/api/billing/credit/hold",
            headers=self._headers(user_id),
            json={"amount": amount},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 402:
            raise InsufficientCredit()
        if r.status_code >= 500:
            raise BillingServiceUnavailable(f"hold: {r.status_code} {_parse_code(r)}")
        raise CreditClientError(f"hold: {r.status_code} {r.text}")

    def debit(self, *, user_id: str, hold_id: str, actual_amount: int) -> dict[str, Any]:
        # Idempotent via holdId — a retry after a successful first attempt
        # gets 409 hold_already_settled, which we surface as CreditClientError
        # (caller should not normally retry debit themselves).
        r = self._send_idempotent(
            "POST", "/api/billing/credit/debit",
            headers=self._headers(user_id),
            json={"holdId": hold_id, "actualAmount": actual_amount},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code >= 500:
            raise BillingServiceUnavailable(f"debit: {r.status_code} {_parse_code(r)}")
        raise CreditClientError(f"debit: {r.status_code} {r.text}")

    def refund(self, *, user_id: str, hold_id: str) -> dict[str, Any] | None:
        # Idempotent via holdId. 409 = debit raced ahead — treated as success
        # (return None) by callers that issued refund as a cleanup.
        r = self._send_idempotent(
            "POST", "/api/billing/credit/refund",
            headers=self._headers(user_id),
            json={"holdId": hold_id},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 409:
            return None
        if r.status_code >= 500:
            raise BillingServiceUnavailable(f"refund: {r.status_code} {_parse_code(r)}")
        raise CreditClientError(f"refund: {r.status_code} {r.text}")

    def close(self) -> None:
        self._client.close()
