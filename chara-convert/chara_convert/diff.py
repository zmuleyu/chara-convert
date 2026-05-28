"""Gap analysis engine — compare a NormalizedCard against a target PlatformSpec."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .converter import _fictionlab_field_value
from .normalizer import NormalizedCard
from .registry import PlatformSpec


@dataclass
class GapReport:
    """Structured report of differences between source card and target platform."""

    target_slug: str
    target_name: str

    # Mapping quality
    perfect_match: list[str] = field(default_factory=list)
    renamed: list[tuple[str, str]] = field(default_factory=list)  # (source_name, target_name)
    truncated: list[tuple[str, int, int]] = field(default_factory=list)  # (field, actual, limit)
    unsupported: list[str] = field(default_factory=list)  # present in card, unknown to target
    missing: list[str] = field(default_factory=list)  # required by target, absent in card

    # Lorebook
    lorebook_supported: bool = False
    lorebook_entries_ok: int = 0
    lorebook_entries_unsupported: int = 0
    lorebook_recursive_diff: bool = False

    # Greetings
    target_greeting_multiple: bool = False
    source_greeting_count: int = 0
    greeting_dropped: int = 0

    # Dialogue format
    source_dialogue_format: str = "Unknown"
    target_preferred_format: str = "Plain"
    format_conversion_needed: bool = False

    # Overall
    ready_score: int = 0  # 0-100 heuristic
    notes: list[str] = field(default_factory=list)


def _detect_dialogue_format(text: str) -> str:
    """Heuristic to detect W++ vs Plain vs XML format."""
    if not text:
        return "Empty"
    stripped = text.strip()
    if stripped.startswith("<") and ">" in stripped[:50]:
        return "XML"
    # W++ uses {{char}} / {{user}} markers heavily plus bracket syntax
    wpp_markers = ["{{char}}:", "{{user}}:", "[", "]"]
    score = sum(1 for m in wpp_markers if m in text[:500])
    if score >= 2:
        return "W++"
    return "Plain"


def _analyze_layered(card: NormalizedCard, target: PlatformSpec) -> GapReport:
    """Gap analysis for layered targets (FictionLab). Fields are reported as
    ``"<layer>.<field>"``; flat-only metrics (lorebook / greeting / dialogue
    format) are left at their defaults — those don't apply to layered output."""
    assert target.layers is not None  # caller-checked
    report = GapReport(target_slug=target.slug, target_name=target.name)

    total = 0
    filled = 0
    for lname, layer in target.layers.items():
        for fname, fspec in layer.fields.items():
            total += 1
            key = f"{lname}.{fname}"
            value = _fictionlab_field_value(card, lname, fname)
            if value:
                report.perfect_match.append(key)
                filled += 1
            elif fspec.required:
                report.missing.append(key)

    report.ready_score = int((filled / total) * 100) if total else 0
    if report.missing:
        report.notes.append(
            f"{len(report.missing)} required layered field(s) need manual input: "
            f"{', '.join(report.missing)}"
        )
    return report


def analyze(card: NormalizedCard, target: PlatformSpec) -> GapReport:
    """Produce a GapReport for converting *card* to *target* platform."""
    if target.layers is not None:
        return _analyze_layered(card, target)

    report = GapReport(
        target_slug=target.slug,
        target_name=target.name,
        lorebook_supported=target.lorebook.supported,
        target_greeting_multiple=target.greeting.multiple,
        target_preferred_format=target.example_dialogue.preferred,
    )

    # Determine which NormalizedCard fields are populated
    card_fields: dict[str, Any] = {}
    for f in ["name", "description", "personality", "scenario",
              "first_mes", "mes_example", "system_prompt",
              "post_history_instructions", "personality_summary",
              "depth_prompt", "alternate_greetings", "creator",
              "creator_notes", "tags"]:
        val = getattr(card, f)
        if val:
            if isinstance(val, list) and val:
                card_fields[f] = val
            elif isinstance(val, str) and val.strip():
                card_fields[f] = val.strip()

    target_names = target.field_names()

    # Perfect match & renamed
    for cname in card_fields:
        if cname in target_names:
            report.perfect_match.append(cname)
            continue
        # Check aliases
        matched = False
        for tname, tfield in target.fields.items():
            if cname in tfield.aliases:
                report.renamed.append((cname, tname))
                matched = True
                break
        if not matched:
            report.unsupported.append(cname)

    # Missing required fields
    for tname, tfield in target.fields.items():
        if tfield.required:
            present = tname in card_fields or any(
                target.get_field(cname) is not None and cname in card_fields
                for cname in card_fields
            )
            if not present:
                report.missing.append(tname)

    # Truncation checks
    for cname, val in card_fields.items():
        if isinstance(val, str):
            tf = target.get_field(cname)
            if tf is not None and tf.max_chars > 0 and len(val) > tf.max_chars:
                report.truncated.append((cname, len(val), tf.max_chars))

    # Lorebook analysis
    if card.lorebook:
        report.lorebook_entries_ok = len(card.lorebook.entries)
        for entry in card.lorebook.entries:
            entry_keys = [
                "name", "keys", "content", "order", "priority",
                "comment", "selective", "secondary_keys",
            ]
            for key in entry_keys:
                if key not in target.lorebook.entry_fields and getattr(entry, key, None):
                    report.lorebook_entries_unsupported += 1
                    break
        if card.lorebook.recursive_scanning and not target.lorebook.recursive_scanning:
            report.lorebook_recursive_diff = True

    # Greeting analysis
    report.source_greeting_count = len(card.alternate_greetings)
    if card.alternate_greetings and not target.greeting.multiple:
        report.greeting_dropped = len(card.alternate_greetings)

    # Dialogue format
    report.source_dialogue_format = _detect_dialogue_format(card.mes_example)
    report.format_conversion_needed = (
        report.source_dialogue_format not in target.example_dialogue.formats
        and report.source_dialogue_format != "Empty"
    )

    # Ready score heuristic
    total_fields = len(card_fields) or 1
    ok = len(report.perfect_match) + len(report.renamed)
    score = int((ok / total_fields) * 100)
    if report.missing:
        score -= len(report.missing) * 15
    if report.truncated:
        score -= len(report.truncated) * 5
    if report.format_conversion_needed:
        score -= 10
    report.ready_score = max(0, min(100, score))

    # Human-readable notes
    if report.missing:
        report.notes.append(
            f"Missing required fields for {target.name}: {', '.join(report.missing)}"
        )
    if report.truncated:
        fields = ", ".join(f"{f} ({a}/{lim})" for f, a, lim in report.truncated)
        report.notes.append(f"Fields exceed target limits: {fields}")
    if report.unsupported:
        report.notes.append(
            f"Fields not supported by {target.name} (will be dropped or stored in extras): "
            f"{', '.join(report.unsupported)}"
        )
    if report.format_conversion_needed:
        report.notes.append(
            f"Example dialogue is in {report.source_dialogue_format} format; "
            f"{target.name} prefers {target.example_dialogue.preferred}. "
            f"Consider converting."
        )
    if report.greeting_dropped:
        report.notes.append(
            f"{report.greeting_dropped} alternate greeting(s) will be dropped "
            f"(platform supports only one greeting)."
        )
    if report.lorebook_recursive_diff:
        report.notes.append(
            "Lorebook recursive scanning is not supported by target; entries will be flattened."
        )
    if target.notes.get("style_hint"):
        report.notes.append(f"Style hint: {target.notes['style_hint']}")

    return report
