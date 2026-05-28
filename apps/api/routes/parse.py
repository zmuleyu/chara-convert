from __future__ import annotations
import dataclasses
import json
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from chara_convert.normalizer import NormalizedCard
from chara_convert.sources.auto import (
    auto_detect_platform,
    CAIParser,
    ChaiParser,
    PolyBuzzParser,
)
from chara_convert.parser import parse_file

router = APIRouter()


class PasteRequest(BaseModel):
    raw: str = Field(min_length=1)
    kind: Literal["paste"]


_PARSERS = {
    "character_ai": CAIParser(),
    "chai": ChaiParser(),
    "polybuzz": PolyBuzzParser(),
}


@router.post("/parse")
async def parse(
    request: Request,
    file: UploadFile | None = File(default=None),
) -> dict:
    """Parse a character card from paste text or file upload."""

    # File upload path
    if file is not None:
        blob = await file.read()
        suffix = Path(file.filename or "").suffix or ""

        # Write to temp file preserving suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(blob)
            tmp_path = tmp.name

        try:
            card: NormalizedCard = parse_file(Path(tmp_path))
        finally:
            Path(tmp_path).unlink()

        # Infer detected platform for file upload
        detected_platform = None
        if suffix == ".png":
            detected_platform = "sillytavern_v2"
        elif suffix == ".json":
            # Peek at JSON to check for spec field
            try:
                json_data = json.loads(blob)
                if isinstance(json_data, dict):
                    spec = json_data.get("spec", "")
                    if isinstance(spec, str) and spec.startswith("chara_card"):
                        detected_platform = "sillytavern_v2"
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "card": dataclasses.asdict(card),
            "detectedPlatform": detected_platform,
            "confidence": 1.0,
        }

    # Paste path: try to parse JSON body
    try:
        body_dict = await request.json()
        body = PasteRequest(**body_dict)
    except (json.JSONDecodeError, ValueError, ValidationError) as e:
        # Let pydantic validation errors return 422
        if isinstance(e, ValidationError):
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=422, detail="Either body or file is required")

    slug, conf = auto_detect_platform(body.raw)

    if slug == "":
        raise HTTPException(status_code=422, detail="no parser matched")

    parser = _PARSERS[slug]
    card: NormalizedCard = parser.parse(body.raw)

    return {
        "card": dataclasses.asdict(card),
        "detectedPlatform": slug,
        "confidence": conf,
    }
