"""Tests for NovelAI lorebook parser."""

from __future__ import annotations

import base64
import json
import struct
import zlib
from pathlib import Path

from chara_convert.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_novelai_lorebook_json() -> None:
    """Parse a standalone NovelAI .lorebook JSON file."""
    data = {
        "entries": [
            {
                "keys": ["magic", "spell"],
                "content": "Magic is powered by moonlight.",
                "insertion_order": 1,
                "priority": 10,
                "enabled": True,
            },
            {
                "keys": ["potion", "elixir"],
                "content": "Potions require precise ingredients.",
                "insertion_order": 2,
                "comment": "Alchemy lore",
            },
        ]
    }
    tmp = FIXTURES / "_tmp_novelai.lorebook"
    tmp.write_text(json.dumps(data), encoding="utf-8")
    try:
        card = parse_file(tmp)
        assert card.name == "NovelAI Lorebook"
        assert card.lorebook is not None
        assert len(card.lorebook.entries) == 2
        assert card.lorebook.entries[0].keys == ["magic", "spell"]
        assert card.lorebook.entries[0].content == "Magic is powered by moonlight."
        assert card.lorebook.entries[0].order == 1
        assert card.lorebook.entries[1].comment == "Alchemy lore"
    finally:
        tmp.unlink()


def test_parse_novelai_png_card() -> None:
    """Parse a NovelAI PNG card with Naidata chunk."""
    lorebook_data = {
        "entries": [
            {
                "keys": ["dragon", "beast"],
                "content": "Dragons are ancient and wise.",
                "insertion_order": 0,
                "enabled": True,
            }
        ]
    }
    raw_json = json.dumps(lorebook_data)
    b64 = base64.b64encode(raw_json.encode("utf-8")).decode("ascii")

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00"

    def chunk(ctype: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + ctype + data + b"\x00\x00\x00\x00"

    idat_raw = zlib.compress(b"\x00\x00")
    naidata = b"Naidata\x00" + b64.encode("ascii")
    png = (
        sig + chunk(b"IHDR", ihdr_data) + chunk(b"tEXt", naidata)
        + chunk(b"IDAT", idat_raw) + chunk(b"IEND", b"")
    )

    tmp = FIXTURES / "_tmp_novelai.png"
    tmp.write_bytes(png)
    try:
        card = parse_file(tmp)
        assert card.name == "NovelAI Lorebook"
        assert card.lorebook is not None
        assert len(card.lorebook.entries) == 1
        assert card.lorebook.entries[0].keys == ["dragon", "beast"]
        assert card.lorebook.entries[0].content == "Dragons are ancient and wise."
    finally:
        tmp.unlink()


def test_standard_json_not_misdetected_as_novelai() -> None:
    """Ensure normal CCv2 JSON is not parsed as NovelAI lorebook."""
    from chara_convert.parser import _is_novelai_lorebook

    standard = {"name": "Test", "first_mes": "Hello", "description": "A test"}
    assert _is_novelai_lorebook(standard) is False

    novelai = {"entries": [{"keys": ["a"], "content": "b"}]}
    assert _is_novelai_lorebook(novelai) is True

    # Edge case: has both entries and name (ambiguous)
    mixed = {"name": "Test", "entries": [{"keys": ["a"], "content": "b"}]}
    assert _is_novelai_lorebook(mixed) is False
