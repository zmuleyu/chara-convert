"""Tests for chara_convert.diff."""

from __future__ import annotations

from pathlib import Path

from chara_convert.diff import _detect_dialogue_format, analyze
from chara_convert.parser import parse_file
from chara_convert.registry import load_spec

FIXTURES = Path(__file__).parent / "fixtures"


def test_perfect_match() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("sillytavern_v2")
    gap = analyze(card, spec)
    assert "name" in gap.perfect_match
    assert gap.target_slug == "sillytavern"
    assert gap.ready_score > 50


def test_janitorai_gaps() -> None:
    card = parse_file(FIXTURES / "sample_card.json")
    spec = load_spec("janitorai")
    gap = analyze(card, spec)
    assert gap.target_slug == "janitorai"
    assert gap.ready_score >= 0


def test_dialogue_format_detection() -> None:
    assert _detect_dialogue_format("{{char}}: hello\n{{user}}: hi") == "W++"
    assert _detect_dialogue_format("User: hello\nBot: hi") == "Plain"
    assert _detect_dialogue_format("") == "Empty"
