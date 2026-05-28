"""Tests for AI enrichment of converted cards (PR 4 cut-4d).

Operates on ``ConvertedCard`` *after* :func:`chara_convert.converter.convert`
has routed source fields. Fills missing-but-required-soft fields like
``character.example_dialogue`` and ``scenario.scenario_intro``.
"""

from __future__ import annotations

from chara_convert.ai import enrich_layered, generate_example_dialogue, generate_scenario_intro
from chara_convert.converter import ConvertedCard
from chara_convert.llm import MockLLMClient
from chara_convert.normalizer import NormalizedCard


def _layered_card(**overrides: dict[str, str]) -> ConvertedCard:
    layers: dict[str, dict[str, str]] = {
        "character": {"name": "Mira", "description": "Mira is a thief in Veridian."},
        "location": {},
        "scenario": {"first_message": "Hey, mate."},
        "lore": {},
    }
    for layer, fields in overrides.items():
        layers.setdefault(layer, {}).update(fields)
    return ConvertedCard(target_slug="fictionlab", layers=layers)


# ---- generate_example_dialogue -------------------------------------------------


def test_generate_example_dialogue_none_client_returns_empty() -> None:
    card = NormalizedCard(name="Mira", description="Thief.", first_mes="Hi.")
    assert generate_example_dialogue(card, client=None) == ""


def test_generate_example_dialogue_calls_llm_with_card_facts() -> None:
    card = NormalizedCard(
        name="Mira",
        description="A thief in Veridian.",
        personality="quick, sarcastic",
        first_mes="Hey there.",
    )
    client = MockLLMClient(responses="{{user}}: Hi.\n{{char}}: Hey. You buying or browsing?")
    out = generate_example_dialogue(card, client=client)
    assert "{{char}}" in out and "{{user}}" in out
    assert len(client.call_log) == 1
    prompt = client.call_log[0]
    assert "Mira" in prompt
    assert "thief in Veridian" in prompt
    assert "quick, sarcastic" in prompt


def test_generate_example_dialogue_skips_when_card_has_no_name() -> None:
    card = NormalizedCard(name="", description="ghost.")
    client = MockLLMClient(responses="should not be called")
    assert generate_example_dialogue(card, client=client) == ""
    assert client.call_log == []


def test_generate_example_dialogue_strips_quote_wrap() -> None:
    card = NormalizedCard(name="Mira", description="Thief.")
    client = MockLLMClient(responses='  "  dialogue body  "  ')
    out = generate_example_dialogue(card, client=client)
    assert out == "dialogue body"


# ---- generate_scenario_intro --------------------------------------------------


def test_generate_scenario_intro_none_client_returns_empty() -> None:
    card = NormalizedCard(name="Mira", description="Thief.", first_mes="Hi.")
    assert generate_scenario_intro(card, client=None) == ""


def test_generate_scenario_intro_calls_llm_with_card_facts() -> None:
    card = NormalizedCard(
        name="Mira",
        description="A thief in Veridian.",
        scenario="The Brass Lantern tavern at dusk.",
        first_mes="Hey there.",
    )
    client = MockLLMClient(responses="The Brass Lantern's hearth crackles as Mira slips into the corner booth.")
    out = generate_scenario_intro(card, client=client)
    assert "Mira" in out
    prompt = client.call_log[0]
    assert "Brass Lantern" in prompt
    assert "thief in Veridian" in prompt


def test_generate_scenario_intro_skips_when_card_empty() -> None:
    card = NormalizedCard()
    client = MockLLMClient(responses="x")
    assert generate_scenario_intro(card, client=client) == ""
    assert client.call_log == []


# ---- enrich_layered -----------------------------------------------------------


def test_enrich_layered_none_client_passthrough() -> None:
    converted = _layered_card()
    norm = NormalizedCard(name="Mira", description="Thief.")
    out = enrich_layered(converted, norm, client=None)
    assert out is converted
    assert out.layers == converted.layers


def test_enrich_layered_fills_missing_example_dialogue() -> None:
    converted = _layered_card()  # character.example_dialogue missing
    assert converted.layers is not None
    assert "example_dialogue" not in converted.layers["character"]
    norm = NormalizedCard(name="Mira", description="Thief.", first_mes="Hi.")
    client = MockLLMClient(
        responses={
            "example dialogue": "{{user}}: Hi.\n{{char}}: Hey.",
            "scenario intro": "Mira ducks into the tavern.",
        }
    )
    out = enrich_layered(converted, norm, client=client)
    assert out.layers is not None
    assert out.layers["character"]["example_dialogue"] == "{{user}}: Hi.\n{{char}}: Hey."
    assert "ai_filled character.example_dialogue" in out.applied_rules


def test_enrich_layered_fills_missing_scenario_intro() -> None:
    converted = _layered_card()  # scenario.scenario_intro missing
    norm = NormalizedCard(name="Mira", scenario="A tavern.", first_mes="Hi.")
    client = MockLLMClient(
        responses={
            "example dialogue": "x",
            "scenario intro": "Mira ducks into the tavern.",
        }
    )
    out = enrich_layered(converted, norm, client=client)
    assert out.layers is not None
    assert out.layers["scenario"]["scenario_intro"] == "Mira ducks into the tavern."
    assert "ai_filled scenario.scenario_intro" in out.applied_rules


def test_enrich_layered_does_not_overwrite_existing_fields() -> None:
    converted = _layered_card(
        character={"example_dialogue": "EXISTING DIALOGUE"},
        scenario={"scenario_intro": "EXISTING INTRO"},
    )
    norm = NormalizedCard(name="Mira", first_mes="Hi.")
    client = MockLLMClient(responses="should not appear")
    out = enrich_layered(converted, norm, client=client)
    assert out.layers is not None
    assert out.layers["character"]["example_dialogue"] == "EXISTING DIALOGUE"
    assert out.layers["scenario"]["scenario_intro"] == "EXISTING INTRO"
    assert client.call_log == []


def test_enrich_layered_skips_unrelated_targets() -> None:
    """Flat (non-layered) ConvertedCard is a no-op."""
    flat = ConvertedCard(target_slug="janitorai", layers=None, fields={"name": "Mira"})
    norm = NormalizedCard(name="Mira")
    client = MockLLMClient(responses="x")
    out = enrich_layered(flat, norm, client=client)
    assert out is flat
    assert client.call_log == []
