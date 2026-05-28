from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chara_convert.registry import list_platforms, load_spec
from chara_convert.converter import convert as cc_convert
from chara_convert.diff import analyze
from chara_convert.normalizer import NormalizedCard

router = APIRouter()


class ConvertRequest(BaseModel):
    card: dict[str, Any]
    targetSlug: str


@router.post("/convert")
async def convert(request: ConvertRequest) -> dict:
    """Convert a character card to a target platform format."""

    # Validate target slug
    targets = list_platforms()
    if request.targetSlug not in targets:
        raise HTTPException(
            status_code=404,
            detail=f"unknown target: {request.targetSlug}"
        )

    # Filter card dict to valid NormalizedCard field names
    valid_fields = {f.name for f in dataclasses.fields(NormalizedCard)}
    filtered_card = {k: v for k, v in request.card.items() if k in valid_fields}

    # Construct NormalizedCard
    card = NormalizedCard(**filtered_card)

    # Load target spec
    spec = load_spec(request.targetSlug)

    # Convert card
    converted = cc_convert(card, spec)

    # Analyze gaps (uses original card, not converted)
    gap = analyze(card, spec)

    # Return response
    return {
        "converted": dataclasses.asdict(converted),
        "gap": dataclasses.asdict(gap),
    }
