"""Tests for AI-assisted PolyBuzz Bio expansion (PR 4 cut-4c)."""

from __future__ import annotations

from chara_convert.llm import MockLLMClient
from chara_convert.sources.polybuzz import PolyBuzzParser, ai_expand_bio


def test_ai_expand_bio_with_none_client_returns_input_unchanged() -> None:
    short = "Mira is a thief in Veridian."
    assert ai_expand_bio(short, client=None) == short


def test_ai_expand_bio_empty_input_returns_empty() -> None:
    assert ai_expand_bio("", client=MockLLMClient()) == ""
    assert ai_expand_bio("   \n  ", client=MockLLMClient()) == ""


def test_ai_expand_bio_calls_llm_and_returns_completion() -> None:
    client = MockLLMClient(responses="Mira is a quick-fingered thief working the back alleys of Veridian.")
    out = ai_expand_bio("Mira is a thief in Veridian.", client=client)
    assert "back alleys of Veridian" in out
    assert len(client.call_log) == 1
    # The short bio is embedded in the prompt.
    assert "Mira is a thief" in client.call_log[0]


def test_ai_expand_bio_strips_surrounding_whitespace_and_quotes() -> None:
    """LLMs often wrap output in stray quotes / whitespace — we clean conservatively."""
    client = MockLLMClient(responses='  "expanded text"  \n')
    out = ai_expand_bio("short", client=client)
    assert out == "expanded text"


def test_polybuzz_parser_uses_ai_client_for_short_bio() -> None:
    raw = (
        "Name: Mira\n"
        "Bio: Thief in Veridian.\n"
        "Personality: clever, quick\n"
        "Greeting: Hey there.\n"
        "Tags: fantasy, rogue\n"
    )
    client = MockLLMClient(responses="Mira is a quick-fingered thief from the back alleys of Veridian, allergic to authority.")
    card = PolyBuzzParser(ai_client=client).parse(raw)
    assert "quick-fingered" in card.description
    # Original short bio is preserved for audit.
    assert card.extras.get("polybuzz_bio_raw") == "Thief in Veridian."
    assert len(client.call_log) == 1


def test_polybuzz_parser_without_ai_client_keeps_bio_unchanged() -> None:
    raw = "Name: Mira\nBio: Thief in Veridian.\nTags: fantasy\n"
    card = PolyBuzzParser().parse(raw)
    assert card.description == "Thief in Veridian."
    # No raw-bio audit key when AI wasn't used.
    assert "polybuzz_bio_raw" not in card.extras


def test_polybuzz_parser_skips_ai_when_bio_already_long() -> None:
    """Don't spend tokens expanding bios that are already substantive."""
    long_bio = "A" * 300
    raw = f"Name: Mira\nBio: {long_bio}\nTags: fantasy\n"
    client = MockLLMClient(responses="this should NOT be called")
    card = PolyBuzzParser(ai_client=client).parse(raw)
    assert card.description == long_bio
    assert client.call_log == []
