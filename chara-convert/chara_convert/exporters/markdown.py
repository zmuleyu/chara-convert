"""Render a ConvertedCard + GapReport into a copy-paste-ready Markdown document."""

from __future__ import annotations

from chara_convert.converter import ConvertedCard
from chara_convert.diff import GapReport

_MANUAL_PLACEHOLDER = "[MANUAL — paste or write content here]"


def _section(title: str, content: str) -> str:
    if not content:
        content = _MANUAL_PLACEHOLDER
    return f"## {title}\n\n{content}\n\n"


def render_markdown(converted: ConvertedCard, gap: GapReport) -> str:
    """Produce a Markdown document ready for copy-paste into the target platform."""
    lines: list[str] = []

    lines.append(f"# Character Card Conversion Report: → {gap.target_name}")
    lines.append("")
    lines.append(f"**Ready Score:** {gap.ready_score}/100")
    lines.append("")

    # Gap summary
    lines.append("## Gap Summary")
    lines.append("")
    if gap.perfect_match:
        lines.append(f"- **Perfect match:** {', '.join(gap.perfect_match)}")
    if gap.renamed:
        pairs = ", ".join(f"{s} → {t}" for s, t in gap.renamed)
        lines.append(f"- **Renamed:** {pairs}")
    if gap.missing:
        lines.append(f"- **Missing (required):** {', '.join(gap.missing)}")
    if gap.unsupported:
        lines.append(f"- **Unsupported (will be dropped):** {', '.join(gap.unsupported)}")
    if gap.truncated:
        pairs = ", ".join(f"{f} ({a} > {lim})" for f, a, lim in gap.truncated)
        lines.append(f"- **Truncated:** {pairs}")
    if gap.format_conversion_needed:
        lines.append(
            f"- **Format conversion needed:** dialogue from "
            f"{gap.source_dialogue_format} → {gap.target_preferred_format}"
        )
    if not any([gap.perfect_match, gap.renamed, gap.missing, gap.unsupported, gap.truncated]):
        lines.append("- All fields map cleanly!")
    lines.append("")

    # Notes
    if gap.notes:
        lines.append("### Notes")
        for note in gap.notes:
            lines.append(f"- {note}")
        lines.append("")

    # Conversion rules applied
    if converted.applied_rules:
        lines.append("### Auto-Conversion Rules Applied")
        for rule in converted.applied_rules:
            lines.append(f"- {rule}")
        lines.append("")

    # Manual gaps
    if converted.manual_gaps:
        lines.append("### Manual Work Required")
        for mg in converted.manual_gaps:
            lines.append(f"- `{mg}` is required but could not be auto-filled.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("# Converted Character Fields")
    lines.append("")
    lines.append(
        f"Copy each section below into the corresponding field in {gap.target_name}."
    )
    lines.append("")

    # Platform-specific rendering
    if converted.target_slug == "nomi":
        lines.append("## Nomi Shared Notes")
        lines.append("")
        lines.append("Copy the content below into your Nomi's Shared Notes > Backstory section.")
        lines.append("")
        if "backstory" in converted.fields:
            lines.append("### Backstory")
            lines.append("")
            lines.append(converted.fields["backstory"])
            lines.append("")
        if "communication_style" in converted.fields:
            lines.append(_section("Communication Style", converted.fields["communication_style"]))
        if "shared_notes" in converted.fields:
            lines.append(_section("Additional Shared Notes", converted.fields["shared_notes"]))
        lines.append("")
        lines.append("> **Tip:** Nomi uses `*action asterisks*` for roleplay. "
                     "Set your communication style to 'roleplay' in Shared Notes for best results.")
        lines.append("")

    elif converted.target_slug == "saucepan":
        lines.append("## Saucepan AI Fields")
        lines.append("")
        lines.append(
            "Copy each section into the corresponding field in "
            "Saucepan AI's character editor."
        )
        lines.append("")
        if "backstory" in converted.fields:
            val = converted.fields["backstory"]
            lines.append("### Backstory (~3000 chars)")
            lines.append("")
            lines.append(val)
            lines.append("")
        if "scenario" in converted.fields:
            val = converted.fields["scenario"]
            lines.append("### Scenario (~1500 chars)")
            lines.append("")
            lines.append(val)
            lines.append("")
        lines.append("")

    elif converted.target_slug == "novelai":
        lines.append("## NovelAI Lorebook")
        lines.append("")
        lines.append(
            "NovelAI is a lorebook-only platform. Character persona should be "
            "embedded in story context or lorebook entries."
        )
        lines.append("")

    else:
        # Standard platform rendering
        for field_name in ["name", "description", "personality", "scenario",
                           "first_mes", "mes_example", "system_prompt",
                           "post_history_instructions"]:
            if field_name in converted.fields:
                val = converted.fields[field_name]
                lines.append(_section(field_name.replace("_", " ").title(), val))

        # Alternate greetings
        if "alternate_greetings" in converted.fields:
            lines.append(_section("Alternate Greetings", converted.fields["alternate_greetings"]))

    # Lorebook (all platforms that support it)
    if converted.lorebook_entries:
        if converted.target_slug == "novelai":
            lines.append("### Lorebook JSON (for import)")
            lines.append("")
            lines.append("```json")
            import json as _json
            novelai_book = {
                "entries": [
                    {
                        "keys": e.get("keys", []),
                        "content": e.get("content", ""),
                        "enabled": e.get("enabled", True),
                        "insertion_order": e.get("insertion_order", e.get("order", 0)),
                        "case_sensitive": e.get("case_sensitive", False),
                        "selective": e.get("selective", False),
                        "secondary_keys": e.get("secondary_keys", []),
                        "constant": e.get("constant", False),
                        "position": e.get("position", "before_char"),
                        "priority": e.get("priority", 0),
                        "comment": e.get("comment", ""),
                    }
                    for e in converted.lorebook_entries
                ]
            }
            lines.append(_json.dumps(novelai_book, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")
        else:
            lines.append("## Lorebook Entries")
            lines.append("")
            for i, entry in enumerate(converted.lorebook_entries, 1):
                lines.append(f"### Entry {i}: {entry.get('name', 'Untitled')}")
                lines.append("")
                lines.append(f"**Keywords:** {', '.join(entry.get('keys', []))}")
                lines.append("")
                lines.append(f"{entry.get('content', '')}")
                lines.append("")
            lines.append("")

    # Tags
    if "tags" in converted.fields:
        lines.append(_section("Tags", converted.fields["tags"]))

    # Creator info
    if "creator" in converted.fields or "creator_notes" in converted.fields:
        lines.append("## Creator Info")
        lines.append("")
        if "creator" in converted.fields:
            lines.append(f"**Creator:** {converted.fields['creator']}")
        if "creator_notes" in converted.fields:
            lines.append(f"**Notes:** {converted.fields['creator_notes']}")
        lines.append("")

    # Dropped / extras hint
    if gap.unsupported:
        lines.append("## Dropped Fields")
        lines.append("")
        lines.append(
            "The following fields were present in the source card but are not "
            f"supported by {gap.target_name}. You may want to manually merge "
            "them into Description or Personality:"
        )
        lines.append("")
        for f in gap.unsupported:
            lines.append(f"- `{f}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"*Generated by keyword-graph card-convert for {gap.target_name}*"
    )

    return "\n".join(lines)
