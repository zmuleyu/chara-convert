"""Tests for chara_convert.converter."""

from __future__ import annotations

from pathlib import Path

from chara_convert.converter import convert
from chara_convert.parser import parse_file
from chara_convert.registry import load_spec

FIXTURES = Path(__file__).parent / "fixtures"


def test_convert_janitorai() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("janitorai")
    converted = convert(card, spec)
    assert "name" in converted.fields
    assert "description" in converted.fields
    assert converted.target_slug == "janitorai"
    assert "merged personality" in " ".join(converted.applied_rules).lower()


def test_convert_sillytavern() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("sillytavern_v2")
    converted = convert(card, spec)
    assert "name" in converted.fields
    assert converted.fields["name"] == "Aria Nightshade"
    assert converted.lorebook_entries


def test_convert_nomi() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("nomi")
    converted = convert(card, spec)
    assert converted.target_slug == "nomi"
    assert "backstory" in converted.fields
    backstory = converted.fields["backstory"]
    assert "Aria Nightshade" in backstory
    assert "Description:" in backstory
    assert "Personality:" in backstory
    assert "Scenario:" in backstory
    assert "merged all persona fields into Nomi Backstory" in converted.applied_rules


def test_convert_saucepan() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("saucepan")
    converted = convert(card, spec)
    assert converted.target_slug == "saucepan"
    assert "backstory" in converted.fields
    assert "scenario" in converted.fields
    assert "merged description + personality into Saucepan Backstory" in converted.applied_rules
    assert "merged scenario + first message into Saucepan Scenario" in converted.applied_rules


def test_convert_novelai() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("novelai")
    converted = convert(card, spec)
    assert converted.target_slug == "novelai"
    assert len(converted.lorebook_entries) == 1
    entry = converted.lorebook_entries[0]
    assert entry["keys"] == ["moon", "phase", "lunar"]
    assert entry["content"] == "Aria's magic is strongest during a full moon."
    assert entry["insertion_order"] == 0
    assert entry["enabled"] is True
    assert entry["position"] == "before_char"
