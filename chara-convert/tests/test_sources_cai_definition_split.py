"""Tests for CAI Definition heuristic paragraph splitter."""

from __future__ import annotations

from chara_convert.sources.cai import CAIParser, split_cai_definition


def test_split_mixed_paragraphs_routes_each_to_correct_bucket() -> None:
    definition = (
        "Thorne is a veteran airship captain.\n\n"
        "Do not break character. Never speak for the user.\n\n"
        "The kingdom of Aurelia has a long history of sky wars.\n\n"
        "The Halcyon is a wooden airship with a small bridge and crowded compartment.\n"
    )
    parts = split_cai_definition(definition)
    assert "veteran airship captain" in parts["description"]
    assert "Do not break character" in parts["instructions"]
    assert "kingdom of Aurelia" in parts["lore"]
    assert "compartment" in parts["location"]


def test_split_instruction_only_definition() -> None:
    definition = "Do not break character.\n\nNever describe user actions.\n"
    parts = split_cai_definition(definition)
    assert "Do not" in parts["instructions"]
    assert "Never" in parts["instructions"]
    assert parts["description"].strip() == ""
    assert parts["lore"].strip() == ""
    assert parts["location"].strip() == ""


def test_split_lore_keywords_route_to_lore() -> None:
    definition = "Magic in this world is bound to the seasons and the history of the old kingdom."
    parts = split_cai_definition(definition)
    assert "Magic" in parts["lore"]
    assert parts["location"].strip() == ""


def test_split_location_keywords_route_to_location() -> None:
    definition = "A dim back-alley room above the spice street, lined with dusty shelves."
    parts = split_cai_definition(definition)
    assert "alley" in parts["location"]
    assert parts["lore"].strip() == ""


def test_cai_parser_integration_populates_definition_split() -> None:
    raw = (
        "Name: Thorne\nGreeting: Hi.\n"
        "Definition: Thorne is a captain.\n\n"
        "Do not speak for the user.\n\n"
        "The kingdom has a long history.\n"
    )
    card = CAIParser().parse(raw)
    assert "Thorne is a captain" in card.extras["cai_definition_description"]
    assert "Do not speak for the user." in card.extras["cai_definition_instructions"]
    assert "kingdom" in card.extras["cai_definition_lore"]
    # The raw Definition blob is still preserved.
    assert "Thorne is a captain" in card.extras["cai_definition"]
