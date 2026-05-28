"""Normalized internal representation for character cards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class LorebookEntry:
    """A single lorebook entry."""

    name: str = ""
    keys: list[str] = field(default_factory=list)
    content: str = ""
    order: int = 0
    priority: int = 0
    comment: str = ""
    selective: bool = False
    secondary_keys: list[str] = field(default_factory=list)


@dataclass
class Lorebook:
    """A collection of lorebook entries."""

    name: str = ""
    entries: list[LorebookEntry] = field(default_factory=list)
    recursive_scanning: bool = False


@dataclass
class NormalizedCard:
    """Platform-agnostic character card representation.

    Fields mirror the de-facto Tavern V2 spec where possible, but any card
    from any source is normalized into this structure.
    """

    # Identity
    name: str = ""
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""

    # Metadata
    creator: str = ""
    creator_notes: str = ""
    character_version: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: int = 0
    modified_at: int = 0

    # Advanced V2/V3 fields
    system_prompt: str = ""
    post_history_instructions: str = ""
    personality_summary: str = ""
    depth_prompt: str = ""
    depth: int = 4

    # Greetings
    alternate_greetings: list[str] = field(default_factory=list)

    # Layer ownership: for layered targets (FictionLab) the opening message belongs to
    # the scenario layer, not the character card. Flat sources default to "character".
    # Converters/exporters consult this when routing first_mes between layers.
    first_mes_owner: Literal["character", "scenario"] = "character"

    # Lorebook
    lorebook: Lorebook | None = None

    # Visual
    avatar: bytes | None = None
    avatar_ext: str = "png"

    # Extras — anything not captured above
    extras: dict[str, Any] = field(default_factory=dict)

    def field_text(self, field_name: str) -> str:
        """Return the text content of a named field (for diff/conversion)."""
        val = getattr(self, field_name, None)
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            return "\n".join(str(v) for v in val)
        return str(val)
