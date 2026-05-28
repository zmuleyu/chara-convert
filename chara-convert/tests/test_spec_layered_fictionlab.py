"""Tests for layered platform specs (FictionLab 4-layer architecture)."""

from __future__ import annotations

from chara_convert.registry import load_spec


def test_spec_fictionlab_has_four_layers() -> None:
    spec = load_spec("fictionlab")
    assert spec.slug == "fictionlab"
    assert spec.name == "FictionLab"
    assert spec.layers is not None
    assert set(spec.layers.keys()) == {"character", "location", "scenario", "lore"}


def test_spec_fictionlab_character_layer_fields() -> None:
    spec = load_spec("fictionlab")
    assert spec.layers is not None
    char = spec.layers["character"]
    assert char.fields["name"].required is True
    assert "description" in char.fields
    assert "personality" in char.fields
    assert "example_dialogue" in char.fields
    assert "appearance" in char.fields


def test_spec_fictionlab_scenario_owns_first_message() -> None:
    spec = load_spec("fictionlab")
    assert spec.layers is not None
    scenario = spec.layers["scenario"]
    assert "first_message" in scenario.fields
    assert scenario.fields["first_message"].required is True
    # First message belongs to scenario, not character card.
    assert "first_message" not in spec.layers["character"].fields


def test_spec_fictionlab_location_and_lore_layers() -> None:
    spec = load_spec("fictionlab")
    assert spec.layers is not None
    loc = spec.layers["location"]
    assert "location_name" in loc.fields
    assert "location_description" in loc.fields
    assert "atmosphere" in loc.fields

    lore = spec.layers["lore"]
    assert "piece_name" in lore.fields
    assert "content" in lore.fields
    assert "activation_condition" in lore.fields


def test_flat_spec_has_no_layers() -> None:
    spec = load_spec("sillytavern_v2")
    assert spec.layers is None
