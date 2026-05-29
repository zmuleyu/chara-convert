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
    # Rough heuristic; OR's usage event gives the actual amount.
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
    so 4xx envelopes go out before SSE headers are flushed and (2) passing in
    the resolved CreditClient + plan."""
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
            # cost missing — bill the held estimate. Metric emission deferred.
            actual_credit = plan["hold_amount"]
        cc.debit(user_id=user_id, hold_id=hold_id, actual_amount=actual_credit)
        settled = True
    except Exception as e:
        # Emit SSE error frame; the `finally` refunds. Do NOT re-raise — that
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
                # orphan-hold cron will pick it up
                pass


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

    # OR path: validate user header + balance BEFORE opening the stream so we
    # can return 4xx with a JSON envelope rather than embedding errors in SSE.
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
