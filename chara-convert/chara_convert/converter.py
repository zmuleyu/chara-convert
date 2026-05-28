"""Preset converter — auto-map fields from NormalizedCard to target PlatformSpec."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalizer import NormalizedCard
from .registry import PlatformSpec


@dataclass
class ConvertedCard:
    """Result of preset conversion: a dict of target-field → content,
    plus metadata about what was changed."""

    target_slug: str
    fields: dict[str, str] = field(default_factory=dict)
    lorebook_entries: list[dict[str, Any]] = field(default_factory=list)
    applied_rules: list[str] = field(default_factory=list)
    manual_gaps: list[str] = field(default_factory=list)


def _normalize_name(val: str) -> str:
    """Clean up a name field."""
    return val.strip()[:120]


def _merge_personality_and_scenario(card: NormalizedCard) -> str:
    """Some platforms expect personality + scenario merged into description."""
    parts = [card.description]
    if card.personality:
        parts.append(f"Personality: {card.personality}")
    if card.scenario:
        parts.append(f"Scenario: {card.scenario}")
    return "\n\n".join(p for p in parts if p)


def _build_nomi_backstory(card: NormalizedCard) -> str:
    """Nomi Shared Notes / Backstory: merge all persona + scenario content."""
    parts: list[str] = []
    if card.name:
        parts.append(f"Name: {card.name}")
    if card.description:
        parts.append(f"Description: {card.description}")
    if card.personality:
        parts.append(f"Personality: {card.personality}")
    if card.scenario:
        parts.append(f"Scenario: {card.scenario}")
    if card.first_mes:
        parts.append(f"First Message: {card.first_mes}")
    if card.mes_example:
        parts.append(f"Example Dialogue: {card.mes_example}")
    return "\n\n".join(parts)


def _build_saucepan_backstory(card: NormalizedCard) -> str:
    """Saucepan Backstory: description + personality."""
    parts: list[str] = []
    if card.description:
        parts.append(card.description)
    if card.personality:
        parts.append(f"Personality: {card.personality}")
    return "\n\n".join(parts)


def _build_saucepan_scenario(card: NormalizedCard) -> str:
    """Saucepan Scenario: scenario + first message."""
    parts: list[str] = []
    if card.scenario:
        parts.append(card.scenario)
    if card.first_mes:
        parts.append(f"First Message: {card.first_mes}")
    return "\n\n".join(parts)


def convert(card: NormalizedCard, target: PlatformSpec) -> ConvertedCard:
    """Run preset conversion rules."""
    result = ConvertedCard(target_slug=target.slug)
    rules: list[str] = []

    # Field remapping: iterate target fields and pull from card
    for tname, tfield in target.fields.items():
        if not tfield.native:
            continue

        val = ""

        # Direct field match
        if hasattr(card, tname) and getattr(card, tname):
            raw = getattr(card, tname)
            if isinstance(raw, str):
                val = raw
            elif isinstance(raw, list):
                val = "\n".join(str(x) for x in raw)

        # Alias match
        if not val:
            for alias in tfield.aliases:
                if hasattr(card, alias) and getattr(card, alias):
                    raw = getattr(card, alias)
                    if isinstance(raw, str):
                        val = raw
                        rules.append(f"mapped {alias} → {tname}")
                    break

        # Special rules per target
        if (
            tname == "description"
            and target.slug == "janitorai"
            and card.personality
            and card.personality not in val
        ):
            val = _merge_personality_and_scenario(card)
            rules.append("merged personality + scenario into description (Janitor AI style)")

        if tname == "backstory" and target.slug == "nomi":
            val = _build_nomi_backstory(card)
            rules.append("merged all persona fields into Nomi Backstory")

        if tname == "backstory" and target.slug == "saucepan":
            val = _build_saucepan_backstory(card)
            rules.append("merged description + personality into Saucepan Backstory")

        if tname == "scenario" and target.slug == "saucepan":
            val = _build_saucepan_scenario(card)
            rules.append("merged scenario + first message into Saucepan Scenario")

        if tname == "first_mes" and not val and card.alternate_greetings:
            val = card.alternate_greetings[0]
            rules.append("used first alternate greeting as primary greeting")

        # Truncation
        if tfield.max_chars > 0 and len(val) > tfield.max_chars:
            val = val[: tfield.max_chars - 3] + "..."
            rules.append(f"truncated {tname} to {tfield.max_chars} chars")

        if val:
            result.fields[tname] = val

    # Name must always be set
    if "name" not in result.fields or not result.fields["name"]:
        result.fields["name"] = "Unnamed Character"
        rules.append("set fallback name (source had none)")

    # Lorebook conversion
    if card.lorebook and target.lorebook.supported:
        for entry in card.lorebook.entries:
            mapped: dict[str, Any] = {
                "name": entry.name,
                "keys": entry.keys,
                "content": entry.content,
            }
            # Map internal field names to target-specific names
            if "order" in target.lorebook.entry_fields:
                mapped["order"] = entry.order
            if "insertion_order" in target.lorebook.entry_fields:
                mapped["insertion_order"] = entry.order
            if "priority" in target.lorebook.entry_fields:
                mapped["priority"] = entry.priority
            if "comment" in target.lorebook.entry_fields:
                mapped["comment"] = entry.comment
            if "selective" in target.lorebook.entry_fields:
                mapped["selective"] = entry.selective
            if "secondary_keys" in target.lorebook.entry_fields:
                mapped["secondary_keys"] = entry.secondary_keys
            # NovelAI-specific fields (defaults)
            if "enabled" in target.lorebook.entry_fields:
                mapped["enabled"] = True
            if "case_sensitive" in target.lorebook.entry_fields:
                mapped["case_sensitive"] = False
            if "constant" in target.lorebook.entry_fields:
                mapped["constant"] = False
            if "position" in target.lorebook.entry_fields:
                mapped["position"] = "before_char"
            result.lorebook_entries.append(mapped)
        rules.append(f"mapped {len(card.lorebook.entries)} lorebook entries")
    elif card.lorebook and not target.lorebook.supported:
        rules.append("lorebook dropped (not supported by target)")

    # Greeting handling
    if card.alternate_greetings:
        if target.greeting.multiple:
            count = target.greeting.max_count or len(card.alternate_greetings)
            kept = card.alternate_greetings[:count]
            result.fields["alternate_greetings"] = "\n---\n".join(kept)
            rules.append(f"kept {len(kept)} alternate greetings")
        else:
            rules.append("alternate greetings dropped (platform supports single greeting)")

    # Dialogue format hint
    if card.mes_example:
        result.fields["_dialogue_format_hint"] = (
            "Original example dialogue may need conversion from detected format."
        )

    result.applied_rules = rules

    # Identify manual gaps
    for tname, tfield in target.fields.items():
        if tfield.required and tname not in result.fields:
            result.manual_gaps.append(tname)

    return result
