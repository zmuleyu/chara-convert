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
PRICING_TABLE: dict[ModelClass, dict[str, dict[str, float]]] = {
    "low": {
        "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
        "moonshotai/kimi-k2":     {"input": 0.60, "output": 2.50},
        "worst_case":             {"input": 0.60, "output": 2.50},
    },
    "high": {
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
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
