"""AI enrichment helpers operating on NormalizedCard / ConvertedCard.

Parser-level AI (CAI Definition reclassify, PolyBuzz bio expand) lives in
``chara_convert.sources``; this package handles post-conversion enrichment
of layered targets where the source had no example dialogue or scenario intro.
"""

from __future__ import annotations

from chara_convert.ai.enrich import (
    enrich_layered,
    generate_example_dialogue,
    generate_scenario_intro,
)

__all__ = ["enrich_layered", "generate_example_dialogue", "generate_scenario_intro"]
