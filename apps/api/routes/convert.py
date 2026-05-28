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

    # Transform for frontend contract:
    # - gap: add derived `fields` bucket map (ok/missing/warn/partial per field path)
    #   because chara_convert's GapReport stores buckets as parallel arrays, but the
    #   frontend GapDashboard expects a single Record<field, bucket> for grid render.
    # - converted: flatten layered output into top-level keys so FieldCard's flat
    #   `converted[field]` lookup works for both flat and layered targets.
    gap_dict = dataclasses.asdict(gap)
    fields_buckets: dict[str, str] = {}
    for fpath in gap.perfect_match:
        fields_buckets[fpath] = "ok"
    for src_name, tgt_name in gap.renamed:
        fields_buckets[tgt_name] = "ok"
    for fpath, _actual, _limit in gap.truncated:
        fields_buckets[fpath] = "warn"
    for fpath in gap.unsupported:
        fields_buckets[fpath] = "warn"
    for fpath in gap.missing:
        fields_buckets[fpath] = "missing"
    gap_dict["fields"] = fields_buckets

    converted_dict = dataclasses.asdict(converted)
    flat_fields: dict[str, Any] = dict(converted_dict.get("fields") or {})
    layers = converted_dict.get("layers") or {}
    for _layer_name, layer_fields in layers.items():
        for fname, fval in (layer_fields or {}).items():
            flat_fields.setdefault(fname, fval)
    # Replace nested structure with flat shape that FieldCard can spread directly.
    converted_dict = {**converted_dict, **flat_fields}

    return {
        "converted": converted_dict,
        "gap": gap_dict,
    }
