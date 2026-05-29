"""USD pricing table and credit unit conversion.

Unit: 1 credit == $0.0001 USD. All credit arithmetic is integer; USD<->credit
conversion happens at module boundaries (hold sizing, OR-reported cost ingest).
"""
from __future__ import annotations

from math import ceil
from typing import Literal

ModelClass = Literal["low", "high"]

USD_PER_CREDIT: float = 0.0001

# USD per 1M tokens, seeded from OR list 2026-05-29. worst_case row is used for
# hold sizing -- must be >= every actual provider row in the same class.
#
# 2026-05-29 refresh notes:
#   - high: claude-3.5-sonnet retired from OR; replaced with claude-sonnet-4.6
#     (same $3/$15 pricing tier). MODEL_BY_CLASS in openrouter.py updated to match.
#   - low/deepseek-chat: OR raised prices to $0.229/$0.914 (was $0.14/$0.28 seed).
#   - low/kimi-k2: now $0.57/$2.30 on OR (small drop from old $0.60/$2.50 seed).
#     worst_case kept at $0.60/$2.50 for ~5-8% headroom against intra-month OR
#     markup changes; drift_check at 20% catches anything larger.
PRICING_TABLE: dict[ModelClass, dict[str, dict[str, float]]] = {
    "low": {
        "deepseek/deepseek-chat": {"input": 0.229, "output": 0.914},
        "moonshotai/kimi-k2":     {"input": 0.57, "output": 2.30},
        "worst_case":             {"input": 0.60, "output": 2.50},
    },
    "high": {
        "anthropic/claude-sonnet-4.6": {"input": 3.00, "output": 15.00},
        "openai/gpt-4o":               {"input": 2.50, "output": 10.00},
        "worst_case":                  {"input": 3.00, "output": 15.00},
    },
}


def usd_to_credit(usd: float) -> int:
    if usd <= 0:
        return 0
    return ceil(usd / USD_PER_CREDIT)


def credit_to_usd(credit: int) -> float:
    return credit * USD_PER_CREDIT


def estimate_max_credit(
    *, prompt_tokens: int, max_tokens: int, model_class: ModelClass,
) -> int:
    """Worst-case credit cost for hold sizing.

    Uses the class's worst_case row so an OR fallback to a pricier provider
    cannot exceed the held amount.
    """
    rates = PRICING_TABLE[model_class]["worst_case"]
    usd = (prompt_tokens * rates["input"] + max_tokens * rates["output"]) / 1_000_000
    return usd_to_credit(usd)
