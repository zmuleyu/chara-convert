"""Structured JSON exporter for converted cards."""

from __future__ import annotations

from typing import Any

from chara_convert.converter import ConvertedCard
from chara_convert.diff import GapReport


def render_json(converted: ConvertedCard, gap: GapReport) -> dict[str, Any]:
    """Produce a structured dict suitable for JSON serialization."""
    return {
        "meta": {
            "target_slug": converted.target_slug,
            "target_name": gap.target_name,
            "ready_score": gap.ready_score,
        },
        "gap": {
            "perfect_match": gap.perfect_match,
            "renamed": gap.renamed,
            "truncated": [
                {"field": f, "actual": a, "limit": lim}
                for f, a, lim in gap.truncated
            ],
            "unsupported": gap.unsupported,
            "missing": gap.missing,
            "notes": gap.notes,
        },
        "converted": {
            "fields": converted.fields,
            "lorebook_entries": converted.lorebook_entries,
            "applied_rules": converted.applied_rules,
            "manual_gaps": converted.manual_gaps,
        },
    }
