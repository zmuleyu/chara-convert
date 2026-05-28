"""Tests for layered-target gap analysis (FictionLab)."""

from __future__ import annotations

from pathlib import Path

from chara_convert.diff import analyze
from chara_convert.normalizer import NormalizedCard
from chara_convert.parser import parse_file
from chara_convert.registry import load_spec

FIXTURES = Path(__file__).parent / "fixtures"


def test_empty_card_reports_layered_missing_with_layer_prefix() -> None:
    report = analyze(NormalizedCard(), load_spec("fictionlab"))
    assert "character.name" in report.missing
    assert "character.description" in report.missing
    assert "scenario.first_message" in report.missing
    assert "scenario.scenario_name" in report.missing


def test_populated_card_reports_layered_perfect_matches() -> None:
    card = NormalizedCard(
        name="Thorne",
        description="An airship captain.",
        first_mes="*adjusts goggles*",
        scenario="The Halcyon drifts above the cloud sea.",
    )
    report = analyze(card, load_spec("fictionlab"))
    assert "character.name" in report.perfect_match
    assert "character.description" in report.perfect_match
    assert "scenario.first_message" in report.perfect_match
    # Required-but-not-supplied still flagged.
    assert "scenario.scenario_name" in report.missing


def test_layered_ready_score_rises_with_more_filled_fields() -> None:
    spec = load_spec("fictionlab")
    empty = analyze(NormalizedCard(), spec).ready_score
    half = analyze(
        NormalizedCard(name="X", description="Y", first_mes="Z"),
        spec,
    ).ready_score
    assert half > empty
    assert 0 <= empty <= 100
    assert 0 <= half <= 100


def test_flat_target_diff_backward_compat() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    report = analyze(card, load_spec("sillytavern_v2"))
    # Flat report shape unchanged: bare field names, not layer-prefixed.
    assert "name" in report.perfect_match
    assert not any("." in entry for entry in report.perfect_match)
