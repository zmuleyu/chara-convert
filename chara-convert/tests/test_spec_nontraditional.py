"""Tests for non-traditional platform specs: Nomi, NovelAI, Saucepan."""

from __future__ import annotations

from chara_convert.registry import load_spec


def test_spec_nomi() -> None:
    spec = load_spec("nomi")
    assert spec.slug == "nomi"
    assert spec.name == "Nomi"
    assert spec.fields["backstory"].required is True
    assert spec.fields["backstory"].native is True
    assert spec.fields["name"].native is False
    assert spec.lorebook.supported is False
    assert spec.greeting.multiple is False


def test_spec_novelai() -> None:
    spec = load_spec("novelai")
    assert spec.slug == "novelai"
    assert spec.name == "NovelAI"
    assert spec.lorebook.supported is True
    assert "insertion_order" in spec.lorebook.entry_fields
    assert "position" in spec.lorebook.entry_fields
    assert "constant" in spec.lorebook.entry_fields
    assert spec.fields["name"].native is False


def test_spec_saucepan() -> None:
    spec = load_spec("saucepan")
    assert spec.slug == "saucepan"
    assert spec.name == "Saucepan AI"
    assert spec.fields["backstory"].max_chars == 3000
    assert spec.fields["scenario"].max_chars == 1500
    assert spec.fields["backstory"].required is True
    assert spec.lorebook.supported is True
    assert spec.lorebook.entry_fields == ["keys", "content"]
