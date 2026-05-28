"""Tests for PolyBuzz source-platform paste-text parser."""

from __future__ import annotations

from chara_convert.sources.polybuzz import PolyBuzzParser


def _full_polybuzz_paste() -> str:
    return (
        "Name: Mira\n"
        "Bio: A bookish witch who runs a tiny apothecary.\n"
        "Personality: introverted, dry-humored, kind\n"
        "Greeting: *looks up from the mortar* Need something for a hangover?\n"
        "Tags: witch, slice-of-life, cozy\n"
    )


def test_detect_with_tags_returns_strong_confidence() -> None:
    assert PolyBuzzParser().detect(_full_polybuzz_paste()) == 0.8


def test_detect_without_tags_returns_weak_confidence() -> None:
    text = "Name: Mira\nBio: A bookish witch.\n"
    assert PolyBuzzParser().detect(text) == 0.5


def test_detect_unrelated_text_returns_zero() -> None:
    assert PolyBuzzParser().detect("Lorem ipsum dolor sit amet.") == 0.0


def test_parse_extracts_polybuzz_fields() -> None:
    card = PolyBuzzParser().parse(_full_polybuzz_paste())
    assert card.name == "Mira"
    assert "bookish witch" in card.description
    assert "introverted" in card.personality
    assert card.first_mes.startswith("*looks up")
    assert card.tags == ["witch", "slice-of-life", "cozy"]
    assert card.extras["source_platform"] == "polybuzz"
