"""PolyBuzz source-platform paste-text parser.

Input shape (per FictionLab dev spec §4.3 / §2 detection rules):
    Name: <one line>
    Bio: <usually short, 50-100 chars>
    Personality: <comma-separated traits or short paragraph>
    Greeting: <opening line; will be routed to Scenario.first_message later>
    Tags: <comma-separated tags — strong signal>

Bio expansion + auto example dialogue generation are AI-assist territory and
deferred to PR 4. This parser only extracts what's literally present.
"""

from __future__ import annotations

import re

from ..llm import LLMClient
from ..normalizer import NormalizedCard
from ..prompts import load_prompt
from .base import SourcePlatformParser

# Bios at/above this length are considered substantive enough to skip AI expansion.
_BIO_EXPAND_THRESHOLD = 180

_LABELS = ("Name", "Bio", "Personality", "Greeting", "Tags")

_LABEL_RE = re.compile(
    r"^(?P<label>" + "|".join(re.escape(lbl) for lbl in _LABELS) + r")\s*:\s*"
    r"(?P<body>.*?)(?=^(?:" + "|".join(re.escape(lbl) for lbl in _LABELS) + r")\s*:|\Z)",
    re.MULTILINE | re.DOTALL,
)


def ai_expand_bio(bio: str, *, client: LLMClient | None) -> str:
    """Expand a short PolyBuzz bio into a fuller FictionLab Description.

    With ``client=None`` the input is returned unchanged (heuristic / Free path).
    With a client provided, the LLM rewrite is returned, stripped of stray
    leading/trailing whitespace and a single surrounding pair of straight quotes
    that some models like to add.
    """
    stripped = bio.strip()
    if not stripped:
        return ""
    if client is None:
        return bio
    prompt = load_prompt("polybuzz_expand_bio", bio=stripped)
    raw = client.complete(prompt, max_tokens=512, temperature=0.4)
    out = raw.strip()
    if len(out) >= 2 and out[0] == out[-1] and out[0] in ('"', "'"):
        out = out[1:-1].strip()
    return out


class PolyBuzzParser(SourcePlatformParser):
    slug = "polybuzz"

    def __init__(self, ai_client: LLMClient | None = None) -> None:
        self._ai_client = ai_client

    def detect(self, raw_text: str) -> float:
        if not raw_text:
            return 0.0
        if not ("Name" in raw_text and "Bio" in raw_text):
            return 0.0
        return 0.8 if "Tags:" in raw_text else 0.5

    def parse(self, raw_text: str) -> NormalizedCard:
        fields = {m.group("label"): m.group("body").strip() for m in _LABEL_RE.finditer(raw_text)}
        tags_raw = fields.get("Tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        bio = fields.get("Bio", "")
        description = bio
        if self._ai_client is not None and 0 < len(bio.strip()) < _BIO_EXPAND_THRESHOLD:
            description = ai_expand_bio(bio, client=self._ai_client)
        card = NormalizedCard(
            name=fields.get("Name", ""),
            description=description,
            personality=fields.get("Personality", ""),
            first_mes=fields.get("Greeting", ""),
            tags=tags,
        )
        card.extras["source_platform"] = self.slug
        if description != bio:
            card.extras["polybuzz_bio_raw"] = bio
        return card
