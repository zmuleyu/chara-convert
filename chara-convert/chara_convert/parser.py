"""Ingest character cards from PNG, JSON, or YAML."""

from __future__ import annotations

import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from .normalizer import Lorebook, LorebookEntry, NormalizedCard


def _read_png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Yield (chunk_type, chunk_data) for each chunk after IHDR."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file")
    idx = 8
    chunks: list[tuple[bytes, bytes]] = []
    while idx < len(data):
        length = struct.unpack(">I", data[idx : idx + 4])[0]
        ctype = data[idx + 4 : idx + 8]
        cdata = data[idx + 8 : idx + 8 + length]
        # crc = data[idx + 8 + length : idx + 12 + length]
        idx += 12 + length
        chunks.append((ctype, cdata))
        if ctype == b"IEND":
            break
    return chunks


def _parse_text_chunk(cdata: bytes) -> tuple[str, str] | None:
    """Parse tEXt or zTXt chunk data into (keyword, text)."""
    null_idx = cdata.find(b"\x00")
    if null_idx < 0:
        return None
    keyword = cdata[:null_idx].decode("latin-1")
    rest = cdata[null_idx + 1 :]
    # For tEXt, rest is plain text
    # For zTXt, rest starts with compression method (0) then zlib data
    if rest[:1] == b"\x00":
        # zTXt compressed
        try:
            text = zlib.decompress(rest[1:]).decode("utf-8")
        except Exception:
            return None
    else:
        text = rest.decode("utf-8", errors="replace")
    return keyword, text


def _extract_card_json_from_png(data: bytes) -> dict[str, Any] | None:
    """Look for 'chara' (V2) or 'ccv3' (V3) text chunks in PNG."""
    chunks = _read_png_chunks(data)
    for ctype, cdata in chunks:
        if ctype not in (b"tEXt", b"zTXt"):
            continue
        parsed = _parse_text_chunk(cdata)
        if parsed is None:
            continue
        keyword, text = parsed
        if keyword in ("chara", "ccv3"):
            try:
                decoded = base64.b64decode(text)
                decompressed = zlib.decompress(decoded)
                return json.loads(decompressed)  # type: ignore[no-any-return]
            except Exception:
                # Some tools store raw JSON in tEXt
                try:
                    return json.loads(text)  # type: ignore[no-any-return]
                except Exception:
                    continue
    return None


def _extract_novelai_lorebook_from_png(data: bytes) -> dict[str, Any] | None:
    """Look for NovelAI 'Naidata' text chunk in PNG (base64 JSON lorebook)."""
    chunks = _read_png_chunks(data)
    for ctype, cdata in chunks:
        if ctype not in (b"tEXt", b"zTXt", b"iTXt"):
            continue
        parsed = _parse_text_chunk(cdata)
        if parsed is None:
            continue
        keyword, text = parsed
        if keyword == "Naidata":
            try:
                decoded = base64.b64decode(text)
                return json.loads(decoded)  # type: ignore[no-any-return]
            except Exception:
                try:
                    return json.loads(text)  # type: ignore[no-any-return]
                except Exception:
                    continue
    return None


def _parse_novelai_lorebook(data: dict[str, Any]) -> NormalizedCard:
    """Convert NovelAI lorebook JSON into NormalizedCard.

    NovelAI lorebooks have no character fields — only lorebook entries.
    We populate the card with a placeholder name and store the lorebook.
    """
    card = NormalizedCard(name="NovelAI Lorebook")
    book = Lorebook()
    for entry in data.get("entries", []):
        book.entries.append(LorebookEntry(
            name=entry.get("name", ""),
            keys=entry.get("keys", []),
            content=entry.get("content", ""),
            order=entry.get("insertion_order", entry.get("order", 0)),
            priority=entry.get("priority", 0),
            comment=entry.get("comment", ""),
            selective=entry.get("selective", False),
            secondary_keys=entry.get("secondary_keys", []),
        ))
    card.lorebook = book
    card.extras["novelai_format"] = "lorebook"
    return card


def _is_novelai_lorebook(data: dict[str, Any]) -> bool:
    """Heuristic: JSON has 'entries' but lacks standard character card fields."""
    has_entries = "entries" in data and isinstance(data["entries"], list)
    lacks_character_fields = not any(
        k in data for k in ("name", "char_name", "first_mes", "char_greeting", "description")
    )
    return has_entries and lacks_character_fields


def _json_to_normalized(data: dict[str, Any]) -> NormalizedCard:
    """Convert parsed card JSON into NormalizedCard."""
    card = NormalizedCard()

    # V1 / V2 flat fields
    card.name = data.get("name", data.get("char_name", ""))
    card.description = data.get("description", data.get("char_persona", ""))
    card.personality = data.get("personality", "")
    card.scenario = data.get("scenario", data.get("world_scenario", ""))
    card.first_mes = data.get("first_mes", data.get("char_greeting", ""))
    card.mes_example = data.get("mes_example", data.get("example_dialogue", ""))

    # Metadata
    card.creator = data.get("creator", "")
    card.creator_notes = data.get("creatorcomment", data.get("creator_notes", ""))
    card.character_version = data.get("character_version", "")
    card.tags = data.get("tags", [])
    if isinstance(card.tags, str):
        card.tags = [t.strip() for t in card.tags.split(",") if t.strip()]
    card.created_at = data.get("create_date", 0)
    card.modified_at = data.get("update_date", 0)

    # Advanced fields
    card.system_prompt = data.get("system_prompt", "")
    card.post_history_instructions = data.get("post_history_instructions", "")
    card.personality_summary = data.get("personality_summary", "")
    card.depth_prompt = data.get("depth_prompt", "")
    card.depth = data.get("depth", 4)

    # Alternate greetings
    card.alternate_greetings = data.get("alternate_greetings", [])

    # Lorebook (V2 spec: data.character_book)
    book = data.get("character_book")
    if book:
        card.lorebook = _json_to_lorebook(book)

    # Extras — anything we didn't explicitly map
    known = {
        "name", "char_name", "description", "char_persona",
        "personality", "scenario", "world_scenario",
        "first_mes", "char_greeting", "mes_example", "example_dialogue",
        "creator", "creatorcomment", "creator_notes", "character_version",
        "tags", "create_date", "update_date",
        "system_prompt", "post_history_instructions",
        "personality_summary", "depth_prompt", "depth",
        "alternate_greetings", "character_book", "data",
    }
    card.extras = {k: v for k, v in data.items() if k not in known}

    # Some cards wrap everything in a "data" key (V3 / Chub style)
    nested = data.get("data")
    if isinstance(nested, dict):
        inner = _json_to_normalized(nested)
        # Merge nested into card, but don't overwrite already-set fields
        for f in ["name", "description", "personality", "scenario",
                  "first_mes", "mes_example", "system_prompt",
                  "post_history_instructions", "alternate_greetings"]:
            if not getattr(card, f) and getattr(inner, f):
                setattr(card, f, getattr(inner, f))
        if not card.lorebook and inner.lorebook:
            card.lorebook = inner.lorebook
        if not card.tags and inner.tags:
            card.tags = inner.tags
        card.extras.update(inner.extras)

    return card


def _json_to_lorebook(data: dict[str, Any]) -> Lorebook:
    """Convert JSON lorebook object to Lorebook."""
    book = Lorebook(
        name=data.get("name", ""),
        recursive_scanning=data.get("recursive_scanning", False),
    )
    for entry in data.get("entries", []):
        book.entries.append(LorebookEntry(
            name=entry.get("name", ""),
            keys=entry.get("keys", []),
            content=entry.get("content", ""),
            order=entry.get("order", 0),
            priority=entry.get("priority", 0),
            comment=entry.get("comment", ""),
            selective=entry.get("selective", False),
            secondary_keys=entry.get("secondary_keys", []),
        ))
    return book


def parse_file(path: Path) -> NormalizedCard:
    """Read a character card from PNG, JSON, or NovelAI lorebook and return NormalizedCard."""
    raw = path.read_bytes()

    # Try PNG first
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        # Standard character card
        json_data = _extract_card_json_from_png(raw)
        if json_data is not None:
            return _json_to_normalized(json_data)
        # NovelAI lorebook card
        novelai_data = _extract_novelai_lorebook_from_png(raw)
        if novelai_data is not None:
            return _parse_novelai_lorebook(novelai_data)
        raise ValueError("PNG file does not contain a recognized character card chunk")

    # Try JSON / YAML
    text = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
        if _is_novelai_lorebook(data):
            return _parse_novelai_lorebook(data)
        return _json_to_normalized(data)
    except json.JSONDecodeError:
        # Minimal YAML fallback (no pyyaml dependency)
        try:
            import yaml  # type: ignore[import-untyped]
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                if _is_novelai_lorebook(data):
                    return _parse_novelai_lorebook(data)
                return _json_to_normalized(data)
        except ImportError:
            pass
        raise ValueError("File is not a valid PNG, JSON, or YAML character card") from None
