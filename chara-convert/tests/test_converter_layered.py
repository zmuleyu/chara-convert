"""Tests for layered-target conversion (FictionLab 4-layer output)."""

from __future__ import annotations

from pathlib import Path

from chara_convert.converter import convert
from chara_convert.normalizer import NormalizedCard
from chara_convert.parser import parse_file
from chara_convert.registry import load_spec

FIXTURES = Path(__file__).parent / "fixtures"


def _basic_card() -> NormalizedCard:
    return NormalizedCard(
        name="Thorne",
        description="An airship captain.",
        personality="gruff, loyal",
        first_mes="*adjusts goggles* Welcome aboard.",
        mes_example="{{char}}: All hands!",
        scenario="The Halcyon drifts above the cloud sea.",
    )


def test_layered_convert_populates_all_four_layers() -> None:
    spec = load_spec("fictionlab")
    converted = convert(_basic_card(), spec)
    assert converted.layers is not None
    assert set(converted.layers.keys()) == {"character", "location", "scenario", "lore"}
    assert converted.layers["character"]["name"] == "Thorne"
    assert "airship captain" in converted.layers["character"]["description"]
    assert "gruff" in converted.layers["character"]["personality"]
    assert "{{char}}" in converted.layers["character"]["example_dialogue"]


def test_first_mes_routes_to_scenario_layer_not_character() -> None:
    spec = load_spec("fictionlab")
    converted = convert(_basic_card(), spec)
    assert converted.layers is not None
    assert converted.layers["scenario"]["first_message"] == "*adjusts goggles* Welcome aboard."
    # first_message must NOT appear in the character layer.
    assert "first_message" not in converted.layers["character"]
    assert "first_mes" not in converted.layers["character"]


def test_cai_definition_instructions_route_to_scenario_custom_instructions() -> None:
    card = _basic_card()
    card.extras["source_platform"] = "character_ai"
    card.extras["cai_definition_instructions"] = "Do not break character. Never speak for the user."
    converted = convert(card, load_spec("fictionlab"))
    assert converted.layers is not None
    assert "Do not break character" in converted.layers["scenario"]["custom_instructions"]


def test_cai_definition_lore_routes_to_lore_content() -> None:
    card = _basic_card()
    card.extras["source_platform"] = "character_ai"
    card.extras["cai_definition_lore"] = "The kingdom of Aurelia has a long history."
    converted = convert(card, load_spec("fictionlab"))
    assert converted.layers is not None
    assert "kingdom of Aurelia" in converted.layers["lore"]["content"]


def test_chai_prompt_instructions_route_to_scenario_custom_instructions() -> None:
    card = _basic_card()
    card.extras["source_platform"] = "chai"
    card.extras["chai_prompt_instructions"] = "Always stay in character."
    converted = convert(card, load_spec("fictionlab"))
    assert converted.layers is not None
    assert "Always stay in character" in converted.layers["scenario"]["custom_instructions"]


def test_flat_target_backward_compat() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    converted = convert(card, load_spec("sillytavern_v2"))
    assert converted.layers is None
    assert "name" in converted.fields
    assert converted.fields["name"] == "Aria Nightshade"


def test_layered_manual_gaps_list_required_fields_not_filled() -> None:
    # An empty card: required fictionlab fields (character.name, character.description,
    # scenario.scenario_name, scenario.first_message, lore.piece_name, lore.content,
    # location.location_name) will all be missing.
    converted = convert(NormalizedCard(), load_spec("fictionlab"))
    assert "character.name" in converted.manual_gaps
    assert "character.description" in converted.manual_gaps
    assert "scenario.first_message" in converted.manual_gaps
    assert "scenario.scenario_name" in converted.manual_gaps
    assert "lore.piece_name" in converted.manual_gaps
    assert "lore.content" in converted.manual_gaps
    assert "location.location_name" in converted.manual_gaps
