"""Tests for Chai source-platform paste-text parser."""

from __future__ import annotations

from chara_convert.sources.chai import ChaiParser


def _full_chai_paste() -> str:
    return (
        "Bot Name: Elaria\n"
        "Bot Description: A wandering elf scholar from the Silvermoon archive.\n"
        "Bot Personality: curious, soft-spoken, stubborn about books\n"
        "First Message: *She glances up from a leather-bound tome.* Oh — you must be the courier.\n"
        "Prompt: You are Elaria, an elf scholar. Do not speak for the user.\n"
    )


def test_detect_strong_signal_returns_high_confidence() -> None:
    parser = ChaiParser()
    score = parser.detect(_full_chai_paste())
    assert score >= 0.8


def test_detect_unrelated_text_returns_zero() -> None:
    parser = ChaiParser()
    score = parser.detect("Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
    assert score == 0.0


def test_parse_full_paste_extracts_all_fields() -> None:
    card = ChaiParser().parse(_full_chai_paste())
    assert card.name == "Elaria"
    assert "Silvermoon archive" in card.description
    assert "curious" in card.personality
    assert card.first_mes.startswith("*She glances up")
    # Prompt is captured raw into extras for later splitting (PR 2 cut-2).
    assert card.extras.get("chai_prompt", "").startswith("You are Elaria")
    assert card.extras.get("source_platform") == "chai"


def test_parse_minimal_paste_handles_missing_optionals() -> None:
    text = "Bot Name: Lyra\nFirst Message: Hi there.\n"
    card = ChaiParser().parse(text)
    assert card.name == "Lyra"
    assert card.first_mes == "Hi there."
    assert card.description == ""
    assert card.personality == ""
    assert "chai_prompt" not in card.extras
