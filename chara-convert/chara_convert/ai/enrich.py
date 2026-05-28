"""Post-conversion AI enrichment for layered targets (PR 4 cut-4d)."""

from __future__ import annotations

from chara_convert.converter import ConvertedCard
from chara_convert.llm import LLMClient
from chara_convert.normalizer import NormalizedCard
from chara_convert.prompts import load_prompt


def _strip_quote_wrap(text: str) -> str:
    out = text.strip()
    if len(out) >= 2 and out[0] == out[-1] and out[0] in ('"', "'"):
        out = out[1:-1].strip()
    return out


def generate_example_dialogue(card: NormalizedCard, *, client: LLMClient | None) -> str:
    """Generate `{{char}}/{{user}}` example dialogue lines for ``card``.

    Returns ``""`` when ``client`` is ``None`` or when ``card`` lacks a name
    (no anchor for the LLM to riff on).
    """
    if client is None or not card.name.strip():
        return ""
    prompt = load_prompt(
        "generate_example_dialogue",
        name=card.name,
        description=card.description,
        personality=card.personality,
        first_mes=card.first_mes,
    )
    return _strip_quote_wrap(client.complete(prompt, max_tokens=512, temperature=0.7))


def generate_scenario_intro(card: NormalizedCard, *, client: LLMClient | None) -> str:
    """Generate a 1-3 sentence scenario intro framing the opening.

    Returns ``""`` when ``client`` is ``None`` or the card has no name AND no
    scenario / first_mes to anchor.
    """
    if client is None:
        return ""
    if not (card.name.strip() or card.scenario.strip() or card.first_mes.strip()):
        return ""
    prompt = load_prompt(
        "generate_scenario_intro",
        name=card.name,
        description=card.description,
        scenario=card.scenario,
        first_mes=card.first_mes,
    )
    return _strip_quote_wrap(client.complete(prompt, max_tokens=512, temperature=0.7))


def enrich_layered(
    converted: ConvertedCard,
    card: NormalizedCard,
    *,
    client: LLMClient | None,
) -> ConvertedCard:
    """Fill missing layered fields (``character.example_dialogue`` /
    ``scenario.scenario_intro``) using ``client``. Mutates and returns
    ``converted``.

    No-op when ``client`` is ``None`` or when ``converted`` is not a layered
    target. Pre-existing field values are never overwritten.
    """
    if client is None or converted.layers is None:
        return converted

    char_layer = converted.layers.setdefault("character", {})
    if not char_layer.get("example_dialogue"):
        dialogue = generate_example_dialogue(card, client=client)
        if dialogue:
            char_layer["example_dialogue"] = dialogue
            converted.applied_rules.append("ai_filled character.example_dialogue")

    scenario_layer = converted.layers.setdefault("scenario", {})
    if not scenario_layer.get("scenario_intro"):
        intro = generate_scenario_intro(card, client=client)
        if intro:
            scenario_layer["scenario_intro"] = intro
            converted.applied_rules.append("ai_filled scenario.scenario_intro")

    return converted
