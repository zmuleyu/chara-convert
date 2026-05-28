"""Tests for chara_convert.parser."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from chara_convert.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_json() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    assert card.name == "Aria Nightshade"
    assert len(card.alternate_greetings) == 2
    assert card.lorebook is not None
    assert card.lorebook.entries[0].keys == ["moon", "phase", "lunar"]


def test_parse_png_minimal() -> None:
    raw_json = json.dumps({"name": "PNGTest", "first_mes": "hi"})
    compressed = zlib.compress(raw_json.encode("utf-8"))
    import base64
    b64 = base64.b64encode(compressed).decode("ascii")

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00"

    def chunk(ctype: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + ctype + data + b"\x00\x00\x00\x00"

    idat_raw = zlib.compress(b"\x00\x00")
    text_data = b"chara\x00" + b64.encode("ascii")
    png = (
        sig + chunk(b"IHDR", ihdr_data) + chunk(b"tEXt", text_data)
        + chunk(b"IDAT", idat_raw) + chunk(b"IEND", b"")
    )

    tmp = FIXTURES / "_tmp_v2.png"
    tmp.write_bytes(png)
    try:
        card = parse_file(tmp)
        assert card.name == "PNGTest"
        assert card.first_mes == "hi"
    finally:
        tmp.unlink()


def test_png_no_card_chunk() -> None:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(ctype: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + ctype + data + b"\x00\x00\x00\x00"

    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00"
    idat = zlib.compress(b"\x00\x00")
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    tmp = FIXTURES / "_tmp_nocard.png"
    tmp.write_bytes(png)
    try:
        with pytest.raises(ValueError, match="does not contain"):
            parse_file(tmp)
    finally:
        tmp.unlink()
