"""Tests for the auto-detect router across source parsers."""

from __future__ import annotations

from chara_convert.sources.auto import auto_detect_platform


def test_auto_detect_chai_paste_wins_with_full_confidence() -> None:
    text = "Bot Name: A\nFirst Message: hi\nPrompt: do something\n"
    slug, score = auto_detect_platform(text)
    assert slug == "chai"
    assert score == 1.0


def test_auto_detect_polybuzz_paste_wins_with_tag_strong_signal() -> None:
    text = "Name: B\nBio: short bio\nTags: a, b\n"
    slug, score = auto_detect_platform(text)
    assert slug == "polybuzz"
    assert score == 0.8


def test_auto_detect_cai_paste_wins_over_polybuzz_when_both_signals_present() -> None:
    # Text contains both Definition: (CAI=1.0) and Tags: (PolyBuzz=0.8) — CAI must win.
    text = (
        "Name: X\nGreeting: hi\nBio: short\n"
        "Tags: a, b\nDefinition: a long blob of character background.\n"
    )
    slug, score = auto_detect_platform(text)
    assert slug == "character_ai"
    assert score == 1.0


def test_auto_detect_unknown_text_returns_zero() -> None:
    slug, score = auto_detect_platform("just some prose with no labels at all.")
    assert score == 0.0
    assert slug == ""
