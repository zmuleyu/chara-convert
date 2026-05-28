"""Tests for AI-assisted CAI Definition reclassification (PR 4 cut-4b)."""

from __future__ import annotations

import json

from chara_convert.llm import MockLLMClient
from chara_convert.sources.cai import CAIParser, ai_resplit_definition


def test_ai_resplit_with_none_client_matches_heuristic() -> None:
    definition = (
        "Thorne is a captain.\n\n"
        "Do not break character.\n\n"
        "The kingdom has history.\n\n"
        "A small bridge compartment.\n"
    )
    parts = ai_resplit_definition(definition, client=None)
    assert "captain" in parts["description"]
    assert "Do not" in parts["instructions"]
    assert "kingdom" in parts["lore"]
    assert "compartment" in parts["location"]


def test_ai_resplit_uses_client_classification() -> None:
    """When the LLM reclassifies an ambiguous paragraph, the LLM wins."""
    # Heuristic alone would route this paragraph to "description" (no keywords).
    # Force the LLM to put it in "lore" instead.
    definition = "The Ember Pact has bound these lands for a thousand turnings."
    canned = json.dumps({"buckets": [{"index": 0, "bucket": "lore"}]})
    client = MockLLMClient(responses=canned)
    parts = ai_resplit_definition(definition, client=client)
    assert "Ember Pact" in parts["lore"]
    assert parts["description"].strip() == ""


def test_ai_resplit_multiple_paragraphs_routed_per_llm() -> None:
    definition = (
        "Thorne hates the cold.\n\n"
        "Never describe user thoughts.\n\n"
        "The Halcyon's bridge is cramped.\n"
    )
    canned = json.dumps(
        {
            "buckets": [
                {"index": 0, "bucket": "description"},
                {"index": 1, "bucket": "instructions"},
                {"index": 2, "bucket": "location"},
            ]
        }
    )
    client = MockLLMClient(responses=canned)
    parts = ai_resplit_definition(definition, client=client)
    assert "hates the cold" in parts["description"]
    assert "Never describe" in parts["instructions"]
    assert "Halcyon" in parts["location"]


def test_ai_resplit_invalid_json_falls_back_to_heuristic() -> None:
    definition = "Do not break character.\n\nThe kingdom is old.\n"
    client = MockLLMClient(responses="not json at all")
    parts = ai_resplit_definition(definition, client=client)
    # Heuristic must still classify cleanly.
    assert "Do not" in parts["instructions"]
    assert "kingdom" in parts["lore"]


def test_ai_resplit_unknown_bucket_falls_back_per_paragraph() -> None:
    definition = "Do not break character.\n\nThe kingdom is old.\n"
    canned = json.dumps(
        {
            "buckets": [
                {"index": 0, "bucket": "garbage_bucket"},
                {"index": 1, "bucket": "lore"},
            ]
        }
    )
    client = MockLLMClient(responses=canned)
    parts = ai_resplit_definition(definition, client=client)
    # Paragraph 0 falls back to heuristic ("Do not" → instructions).
    assert "Do not" in parts["instructions"]
    # Paragraph 1 uses LLM classification.
    assert "kingdom" in parts["lore"]


def test_ai_resplit_empty_text() -> None:
    parts = ai_resplit_definition("", client=MockLLMClient())
    assert parts == {"description": "", "instructions": "", "lore": "", "location": ""}


def test_cai_parser_uses_ai_client_when_provided() -> None:
    raw = (
        "Name: Thorne\nGreeting: Hi.\n"
        "Definition: Thorne is a captain.\n\n"
        "Never speak for the user.\n\n"
        "The Ember Pact is ancient law.\n"
    )
    canned = json.dumps(
        {
            "buckets": [
                {"index": 0, "bucket": "description"},
                {"index": 1, "bucket": "instructions"},
                {"index": 2, "bucket": "lore"},
            ]
        }
    )
    client = MockLLMClient(responses=canned)
    card = CAIParser(ai_client=client).parse(raw)
    assert "Thorne is a captain" in card.extras["cai_definition_description"]
    assert "Never speak" in card.extras["cai_definition_instructions"]
    assert "Ember Pact" in card.extras["cai_definition_lore"]
    # Prompt actually went to the mock.
    assert len(client.call_log) == 1
    assert "Ember Pact" in client.call_log[0]


def test_cai_parser_without_ai_client_remains_heuristic() -> None:
    raw = (
        "Name: Thorne\nGreeting: Hi.\n"
        "Definition: Thorne is a captain.\n\nDo not break character.\n"
    )
    card = CAIParser().parse(raw)
    # Heuristic path still works (PR 1-3 contract preserved).
    assert "Thorne is a captain" in card.extras["cai_definition_description"]
    assert "Do not break character." in card.extras["cai_definition_instructions"]
