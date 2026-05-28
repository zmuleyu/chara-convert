"""Tests for layered Markdown exporter (FictionLab 4-layer output)."""

from __future__ import annotations

from chara_convert.converter import convert
from chara_convert.diff import analyze
from chara_convert.exporters.markdown import render_markdown
from chara_convert.normalizer import NormalizedCard
from chara_convert.registry import load_spec


def _card_with_splits() -> NormalizedCard:
    card = NormalizedCard(
        name="Thorne",
        description="An airship captain.",
        personality="gruff, loyal",
        first_mes="*adjusts goggles* Welcome aboard.",
        scenario="The Halcyon drifts above the cloud sea.",
    )
    card.extras["source_platform"] = "character_ai"
    card.extras["cai_definition_instructions"] = "Do not break character."
    card.extras["cai_definition_lore"] = "Aurelia kingdom has a long history."
    card.extras["cai_definition_location"] = "A dim back-alley room above the spice street."
    return card


def _render() -> str:
    card = _card_with_splits()
    spec = load_spec("fictionlab")
    return render_markdown(convert(card, spec), analyze(card, spec))


def test_layered_render_has_four_layer_sections() -> None:
    md = _render()
    assert "## Character Card" in md
    assert "## Location Card" in md
    assert "## Scenario" in md
    assert "## Lore" in md


def test_layered_render_routes_first_message_to_scenario() -> None:
    md = _render()
    scenario_pos = md.index("## Scenario")
    char_pos = md.index("## Character Card")
    greeting = "*adjusts goggles* Welcome aboard."
    greeting_pos = md.index(greeting)
    # Greeting must appear AFTER the Scenario header, not in the Character section.
    assert greeting_pos > scenario_pos
    # And the Character Card section should not contain the greeting.
    character_section = md[char_pos : md.index("## Location Card")]
    assert greeting not in character_section


def test_layered_render_emits_custom_instructions_in_scenario() -> None:
    md = _render()
    scenario_pos = md.index("## Scenario")
    lore_pos = md.index("## Lore")
    scenario_section = md[scenario_pos:lore_pos]
    assert "Do not break character" in scenario_section


def test_layered_render_emits_lore_content() -> None:
    md = _render()
    lore_pos = md.index("## Lore")
    lore_tail = md[lore_pos:]
    assert "Aurelia kingdom" in lore_tail


def test_layered_render_lists_manual_gaps_with_layer_prefix() -> None:
    card = NormalizedCard()  # empty card — many required fields missing
    spec = load_spec("fictionlab")
    md = render_markdown(convert(card, spec), analyze(card, spec))
    assert "Manual Work Required" in md
    assert "character.name" in md
    assert "scenario.first_message" in md
    assert "lore.piece_name" in md
