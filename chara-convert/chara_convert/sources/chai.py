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

# Imperative-instruction sentence starters (per FictionLab dev spec §4.2).
# Case-insensitive prefix match against sentence-leading words.
_INSTRUCTION_PREFIXES = (
    "do not",
    "don't",
    "always",
    "never",
    "avoid",
    "make sure",
    "ensure",
    "remember to",
    "use",
    "respond",
)

# Split into sentences on `.`, `!`, `?` while keeping the delimiter, and also
# treat hard newlines as sentence boundaries (Chai prompts often use line breaks
# as imperative separators).
_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?\n]?", re.DOTALL)


def _is_instruction(sentence: str) -> bool:
    s = sentence.strip().lower()
    return any(s.startswith(p) for p in _INSTRUCTION_PREFIXES)


def split_chai_prompt(prompt: str) -> dict[str, str]:
    """Heuristic split of a Chai Prompt body into instructions vs. rest.

    Instructions: sentences starting with imperative cues (Do not, Always, Never,
    etc.). Rest: everything else. Full character/scenario disambiguation inside
    *rest* is deferred to a later AI-assisted pass (PR 4).
    """
    if not prompt:
        return {"instructions": "", "rest": ""}

    instructions: list[str] = []
    rest_parts: list[str] = []
    for match in _SENTENCE_RE.finditer(prompt):
        sentence = match.group(0)
        if not sentence.strip():
            continue
        if _is_instruction(sentence):
            instructions.append(sentence.strip())
        else:
            rest_parts.append(sentence.strip())

    return {
        "instructions": " ".join(instructions),
        "rest": " ".join(rest_parts),
    }

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
            split = split_chai_prompt(prompt)
            if split["instructions"]:
                card.extras["chai_prompt_instructions"] = split["instructions"]
            if split["rest"]:
                card.extras["chai_prompt_rest"] = split["rest"]
        return card
