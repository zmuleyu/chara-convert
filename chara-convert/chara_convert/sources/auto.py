"""Source-platform auto-detect router.

Runs every registered parser's ``detect()`` against the input and returns the
slug + confidence of the highest-scoring candidate. Returns ``("", 0.0)`` when
no parser reaches a positive confidence.
"""

from __future__ import annotations

from .base import SourcePlatformParser
from .cai import CAIParser
from .chai import ChaiParser
from .polybuzz import PolyBuzzParser

# Order: most discriminating first to break ties in stable iteration.
_REGISTERED: tuple[SourcePlatformParser, ...] = (CAIParser(), ChaiParser(), PolyBuzzParser())


def auto_detect_platform(raw_text: str) -> tuple[str, float]:
    """Return ``(slug, confidence)`` of the best-matching source parser."""
    if not raw_text:
        return ("", 0.0)
    best_slug = ""
    best_score = 0.0
    for parser in _REGISTERED:
        score = parser.detect(raw_text)
        if score > best_score:
            best_score = score
            best_slug = parser.slug
    return (best_slug, best_score)
