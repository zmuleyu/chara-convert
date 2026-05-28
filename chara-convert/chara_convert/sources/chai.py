"""Chai source-platform paste-text parser.

Input shape (per FictionLab dev spec §2 detection rules):
    Bot Name: <one line>
    Bot Description: <multi-line until next label>
    Bot Personality: <multi-line>
    First Message: <multi-line>
    Prompt: <multi-line, may mix scenario / character / instructions>

Detection is keyed on the ``Prompt:`` strong signal, with required keywords
``Bot Name`` and ``First Message``. The ``Prompt`` body is captured verbatim
into ``extras["chai_prompt"]`` for later layered-aware splitting (PR 2 cut-2);
this parser intentionally does not attempt that split.
"""

from __future__ import annotations

import re

from ..normalizer import NormalizedCard
from .base import SourcePlatformParser

_LABELS = ("Bot Name", "Bot Description", "Bot Personality", "First Message", "Prompt")

# Match "<Label>:" at the start of a line; capture body up to the next label
# or end of text. Multiline + dotall so values may span paragraphs.
_LABEL_RE = re.compile(
    r"^(?P<label>" + "|".join(re.escape(lbl) for lbl in _LABELS) + r")\s*:\s*"
    r"(?P<body>.*?)(?=^(?:" + "|".join(re.escape(lbl) for lbl in _LABELS) + r")\s*:|\Z)",
    re.MULTILINE | re.DOTALL,
)


class ChaiParser(SourcePlatformParser):
    slug = "chai"

    def detect(self, raw_text: str) -> float:
        if not raw_text:
            return 0.0
        required = ("Bot Name", "First Message")
        if not all(kw in raw_text for kw in required):
            return 0.0
        # "Prompt:" is the strong discriminator vs. CAI/PolyBuzz (per spec §2).
        return 1.0 if "Prompt:" in raw_text else 0.6

    def parse(self, raw_text: str) -> NormalizedCard:
        fields = {m.group("label"): m.group("body").strip() for m in _LABEL_RE.finditer(raw_text)}
        card = NormalizedCard(
            name=fields.get("Bot Name", ""),
            description=fields.get("Bot Description", ""),
            personality=fields.get("Bot Personality", ""),
            first_mes=fields.get("First Message", ""),
        )
        card.extras["source_platform"] = self.slug
        prompt = fields.get("Prompt", "")
        if prompt:
            card.extras["chai_prompt"] = prompt
        return card
