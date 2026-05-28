"""Character.AI source-platform paste-text parser.

Input shape (per FictionLab dev spec §4.1 / §2 detection rules):
    Name: <one line>
    Description: <short identity blurb>
    Personality: <traits>
    Greeting: <opening line; routes to Scenario.first_message later>
    Scenario: <setting context; routes to Scenario.intro + Location later>
    Example Dialogue: <may use {{char}} / {{user}} markers>
    Definition: <long mixed blob — character background, instructions,
                 lore, location all woven together>

Detection requires the ``Definition:`` strong signal (per spec §2) to
discriminate from PolyBuzz's "Name + Bio" shape. The Definition body itself
is captured verbatim into ``extras["cai_definition"]``; paragraph-level
splitting into Character/Scenario/Lore/Instructions layers is the next cut
(cut-4b, per spec §4.1 lines 257-280).
"""

from __future__ import annotations

import json
import re

from ..llm import LLMClient
from ..normalizer import NormalizedCard
from ..prompts import load_prompt
from .base import SourcePlatformParser

_VALID_BUCKETS = ("description", "instructions", "lore", "location")

_LABELS = (
    "Name",
    "Description",
    "Personality",
    "Greeting",
    "Scenario",
    "Example Dialogue",
    "Definition",
)

_LABEL_RE = re.compile(
    r"^(?P<label>" + "|".join(re.escape(lbl) for lbl in _LABELS) + r")\s*:\s*"
    r"(?P<body>.*?)(?=^(?:" + "|".join(re.escape(lbl) for lbl in _LABELS) + r")\s*:|\Z)",
    re.MULTILINE | re.DOTALL,
)

# Definition heuristic split — per FictionLab dev spec §4.1 paragraph rules.
# Priority order: most discriminating bucket wins when a paragraph hits multiple.
_INSTRUCTION_PATTERNS = (
    re.compile(r"\b(do not|don't|always|never|avoid|make sure|ensure)\b", re.IGNORECASE),
)
_LOCATION_PATTERNS = (
    re.compile(
        r"\b(room|station|compartment|street|alley|hall|chamber|house|castle|bridge)\b",
        re.IGNORECASE,
    ),
)
_LORE_PATTERNS = (
    re.compile(r"\b(world|magic|kingdom|history|empire|legend|ancient|prophecy)\b", re.IGNORECASE),
)


def _classify_paragraph(paragraph: str) -> str:
    """Return bucket name: instructions / location / lore / description."""
    if any(p.search(paragraph) for p in _INSTRUCTION_PATTERNS):
        return "instructions"
    if any(p.search(paragraph) for p in _LOCATION_PATTERNS):
        return "location"
    if any(p.search(paragraph) for p in _LORE_PATTERNS):
        return "lore"
    return "description"


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _empty_buckets() -> dict[str, list[str]]:
    return {b: [] for b in _VALID_BUCKETS}


def split_cai_definition(text: str) -> dict[str, str]:
    """Heuristic split of a CAI Definition blob into 4 layered buckets.

    Returns ``{"description": ..., "instructions": ..., "lore": ..., "location": ...}``.
    Paragraphs are blank-line separated. For AI-assisted re-classification of
    ambiguous paragraphs, see :func:`ai_resplit_definition` (PR 4 cut-4b).
    """
    buckets = _empty_buckets()
    if not text:
        return {k: "" for k in buckets}
    for para in _split_paragraphs(text):
        buckets[_classify_paragraph(para)].append(para)
    return {k: "\n\n".join(v) for k, v in buckets.items()}


def ai_resplit_definition(text: str, *, client: LLMClient | None) -> dict[str, str]:
    """LLM-assisted variant of :func:`split_cai_definition`.

    When ``client`` is ``None`` this is identical to the heuristic split. When
    a client is provided, the paragraphs are sent for re-classification; the
    LLM's verdict wins per-paragraph. Malformed JSON or invalid buckets fall
    back to the heuristic for the affected paragraph(s), so the function is
    always safe to call.
    """
    if not text:
        return {k: "" for k in _empty_buckets()}
    if client is None:
        return split_cai_definition(text)

    paragraphs = _split_paragraphs(text)
    numbered = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(paragraphs))
    prompt = load_prompt("cai_resplit_definition", paragraphs=numbered)
    raw = client.complete(prompt, max_tokens=512, temperature=0.0)

    llm_buckets: dict[int, str] = {}
    try:
        payload = json.loads(raw)
        for entry in payload.get("buckets", []):
            idx = entry.get("index")
            bucket = entry.get("bucket")
            if isinstance(idx, int) and bucket in _VALID_BUCKETS:
                llm_buckets[idx] = bucket
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Whole response unusable — every paragraph falls back below.
        pass

    routed = _empty_buckets()
    for i, para in enumerate(paragraphs):
        bucket = llm_buckets.get(i) or _classify_paragraph(para)
        routed[bucket].append(para)
    return {k: "\n\n".join(v) for k, v in routed.items()}


class CAIParser(SourcePlatformParser):
    slug = "character_ai"

    def __init__(self, ai_client: LLMClient | None = None) -> None:
        self._ai_client = ai_client

    def detect(self, raw_text: str) -> float:
        if not raw_text:
            return 0.0
        # Spec §2: Definition: is the binary discriminator.
        return 1.0 if "Definition:" in raw_text else 0.0

    def parse(self, raw_text: str) -> NormalizedCard:
        fields = {m.group("label"): m.group("body").strip() for m in _LABEL_RE.finditer(raw_text)}
        card = NormalizedCard(
            name=fields.get("Name", ""),
            description=fields.get("Description", ""),
            personality=fields.get("Personality", ""),
            first_mes=fields.get("Greeting", ""),
            scenario=fields.get("Scenario", ""),
            mes_example=fields.get("Example Dialogue", ""),
        )
        card.extras["source_platform"] = self.slug
        definition = fields.get("Definition", "")
        if definition:
            card.extras["cai_definition"] = definition
            split = ai_resplit_definition(definition, client=self._ai_client)
            for bucket, content in split.items():
                if content:
                    card.extras[f"cai_definition_{bucket}"] = content
        return card
