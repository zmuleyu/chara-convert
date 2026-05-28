"""Tests for Character.AI source-platform paste-text parser."""

from __future__ import annotations

from chara_convert.sources.cai import CAIParser


def _full_cai_paste() -> str:
    return (
        "Name: Thorne\n"
        "Description: A grizzled airship captain.\n"
        "Personality: gruff, loyal, secretly sentimental\n"
        "Greeting: *adjusts goggles* Welcome aboard the Halcyon.\n"
        "Scenario: The airship Halcyon drifts above the cloud sea.\n"
        "Example Dialogue: {{char}}: All hands to stations!\n"
        "Definition: Captain Thorne is a veteran of the Sky War. "
        "He has piloted the Halcyon for twelve years. "
        "Do not break character. Never speak for the user.\n"
    )


def test_detect_with_definition_returns_full_confidence() -> None:
    assert CAIParser().detect(_full_cai_paste()) == 1.0


def test_detect_without_definition_returns_zero() -> None:
    # Even with Name + Greeting + Personality, CAI requires the Definition signal.
    text = "Name: A\nGreeting: hi\nPersonality: kind\n"
    assert CAIParser().detect(text) == 0.0


def test_detect_unrelated_text_returns_zero() -> None:
    assert CAIParser().detect("Lorem ipsum dolor sit amet.") == 0.0


def test_parse_extracts_cai_fields() -> None:
    card = CAIParser().parse(_full_cai_paste())
    assert card.name == "Thorne"
    assert "airship captain" in card.description
    assert "gruff" in card.personality
    assert card.first_mes.startswith("*adjusts goggles")
    assert "cloud sea" in card.scenario
    assert "{{char}}" in card.mes_example
    # Definition is preserved verbatim for cut-4b's heuristic splitter.
    assert "Sky War" in card.extras["cai_definition"]
    assert card.extras["source_platform"] == "character_ai"
