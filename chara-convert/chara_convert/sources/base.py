"""Abstract base class for source-platform paste-text parsers.

Unlike the file-based ``parser.parse_file`` (which handles PNG/JSON/YAML exports
from open platforms like SillyTavern), source parsers ingest raw text a user
copy-pastes from a closed platform's UI (Character.AI, Chai, PolyBuzz).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..normalizer import NormalizedCard


class SourcePlatformParser(ABC):
    """Parse raw pasted text from a closed source platform."""

    #: Slug stored under ``NormalizedCard.extras["source_platform"]`` on parse.
    slug: str = ""

    @abstractmethod
    def detect(self, raw_text: str) -> float:
        """Return confidence in [0.0, 1.0] that *raw_text* came from this platform."""

    @abstractmethod
    def parse(self, raw_text: str) -> NormalizedCard:
        """Extract fields from *raw_text* into a NormalizedCard."""
