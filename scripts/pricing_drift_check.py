#!/usr/bin/env python3
"""Compare PRICING_TABLE against OR's live model list. Exit 1 if any per-token
price drifts > 20%. Designed to run monthly; output is consumed by an external
notifier (out of scope here)."""
from __future__ import annotations

import json
import sys
import urllib.request

# Add the chara-convert package to sys.path when the script is invoked from repo root.
_HERE = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "chara-convert"))

from chara_convert.llm.pricing import PRICING_TABLE  # noqa: E402

OR_MODELS = "https://openrouter.ai/api/v1/models"
THRESHOLD = 0.20


def main() -> int:
    req = urllib.request.Request(OR_MODELS, headers={"User-Agent": "drift-guard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed URL
        data = json.load(resp)
    live: dict[str, dict[str, float]] = {}
    for m in data.get("data", []):
        slug = m.get("id")
        pricing = m.get("pricing") or {}
        if not slug:
            continue
        try:
            # OR's pricing is per-token strings -> convert to per-1M float
            live[slug] = {
                "input":  float(pricing["prompt"]) * 1_000_000,
                "output": float(pricing["completion"]) * 1_000_000,
            }
        except (KeyError, TypeError, ValueError):
            continue

    drifts: list[str] = []
    for cls_table in PRICING_TABLE.values():
        for slug, rates in cls_table.items():
            if slug == "worst_case":
                continue
            seen = live.get(slug)
            if not seen:
                drifts.append(f"{slug}: missing in OR live list")
                continue
            for k in ("input", "output"):
                a, b = rates[k], seen[k]
                if a == 0:
                    continue
                if abs(a - b) / a > THRESHOLD:
                    drifts.append(f"{slug}/{k}: seed={a} live={b:.4f} drift={abs(a-b)/a:.0%}")

    if drifts:
        print("PRICING DRIFT DETECTED:")
        for d in drifts:
            print("  - " + d)
        return 1
    print("pricing table within 20% of OR live rates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
