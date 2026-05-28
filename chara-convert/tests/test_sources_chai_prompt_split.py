"""Tests for Chai prompt heuristic splitting (instructions vs rest)."""

from __future__ import annotations

from chara_convert.sources.chai import ChaiParser, split_chai_prompt


def test_split_mixed_prompt_separates_instructions_and_rest() -> None:
    prompt = (
        "You are Elaria, a wandering elf scholar.\n"
        "She lives in the Silvermoon archive.\n"
        "Do not speak for the user.\n"
        "Always stay in character.\n"
    )
    parts = split_chai_prompt(prompt)
    assert "Do not speak for the user." in parts["instructions"]
    assert "Always stay in character." in parts["instructions"]
    assert "You are Elaria" in parts["rest"]
    assert "Silvermoon archive" in parts["rest"]
    # Instructions should not leak into rest.
    assert "Do not speak for the user." not in parts["rest"]


def test_split_instruction_only_prompt() -> None:
    prompt = "Do not break character.\nNever describe user actions.\nAlways respond in first person.\n"
    parts = split_chai_prompt(prompt)
    assert "Do not break character." in parts["instructions"]
    assert "Never describe user actions." in parts["instructions"]
    assert "Always respond in first person." in parts["instructions"]
    assert parts["rest"].strip() == ""


def test_split_no_instruction_prompt() -> None:
    prompt = "Elaria is curious and stubborn. She loves dusty tomes and dislikes loud crowds."
    parts = split_chai_prompt(prompt)
    assert parts["instructions"].strip() == ""
    assert "Elaria is curious" in parts["rest"]


def test_split_empty_prompt() -> None:
    parts = split_chai_prompt("")
    assert parts == {"instructions": "", "rest": ""}


def test_chai_parser_integration_populates_split_extras() -> None:
    raw = (
        "Bot Name: Elaria\n"
        "First Message: Hi.\n"
        "Prompt: You are an elf scholar. Do not speak for the user.\n"
    )
    card = ChaiParser().parse(raw)
    assert "Do not speak for the user." in card.extras["chai_prompt_instructions"]
    assert "You are an elf scholar." in card.extras["chai_prompt_rest"]
    # Original chai_prompt is still preserved for cut-3+ debugging / re-splits.
    assert card.extras["chai_prompt"].startswith("You are an elf scholar.")
