from __future__ import annotations

import os
from typing import AsyncGenerator, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chara_convert.ai.enrich import build_field_prompt
from chara_convert.llm.factory import build_ai_client_or_none
from chara_convert.llm.mock import MockLLMClient
from dataclasses import fields
from chara_convert.normalizer import NormalizedCard

router = APIRouter()

ALLOWED_FIELDS: set[str] = {
    "personality",
    "scenario",
    "first_message",
    "mes_example",
    "description",
    "appearance",
}


class EnrichRequest(BaseModel):
    card: dict
    field: Literal[
        "personality",
        "scenario",
        "first_message",
        "mes_example",
        "description",
        "appearance",
    ]


def _client():
    """Build LLM client, respecting CHARA_CONVERT_AI_MOCK env var."""
    mock = os.environ.get("CHARA_CONVERT_AI_MOCK")
    if mock:
        return MockLLMClient(responses=mock)
    client, _status = build_ai_client_or_none()
    return client


async def _stream(prompt: str) -> AsyncGenerator[bytes, None]:
    """Stream completion chunks as SSE data lines."""
    client = _client()
    if client is None:
        yield b"data: (no LLM client available)\n\n"
        return
    text = client.complete(prompt, max_tokens=400, temperature=0.7)
    for chunk in text.split(" "):
        yield f"data: {chunk} \n\n".encode()


@router.post("/ai/enrich")
async def enrich(body: EnrichRequest):
    """Stream AI-enriched text for a single card field."""
    if body.field not in ALLOWED_FIELDS:
        raise HTTPException(status_code=422, detail="unsupported field")
    known = {f.name for f in fields(NormalizedCard)}
    safe = {k: v for k, v in body.card.items() if k in known}
    # Frontend may use first_message; NormalizedCard uses first_mes.
    if 'first_message' in body.card and 'first_mes' not in safe:
        safe['first_mes'] = body.card['first_message']
    card = NormalizedCard(**safe)
    prompt = build_field_prompt(card, body.field)
    return StreamingResponse(_stream(prompt), media_type="text/event-stream")
