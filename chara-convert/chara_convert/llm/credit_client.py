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
            return None
        raise CreditClientError(f"refund: {r.status_code} {r.text}")

    def close(self) -> None:
        self._client.close()
