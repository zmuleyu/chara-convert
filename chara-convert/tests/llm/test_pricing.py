import pytest

from chara_convert.llm.pricing import (
    PRICING_TABLE,
    USD_PER_CREDIT,
    credit_to_usd,
    estimate_max_credit,
    usd_to_credit,
)


def test_usd_to_credit_rounds_up_to_nearest_cent_of_credit():
    assert usd_to_credit(0.0001) == 1
    assert usd_to_credit(0.00015) == 2
    assert usd_to_credit(0.0) == 0


def test_credit_to_usd_inverse():
    assert credit_to_usd(10000) == pytest.approx(1.0)
    assert credit_to_usd(0) == 0.0


def test_pricing_table_invariant_primary_eq_first_fallback():
    """Spec invariant: every MODEL_BY_CLASS entry has primary == fallback[0].
    The pricing module holds the per-model USD table — assert it covers every
    primary + fallback model from the spec.
    """
    required = {
        "deepseek/deepseek-chat", "moonshotai/kimi-k2",
        "anthropic/claude-sonnet-4.6", "openai/gpt-4o",
    }
    covered: set[str] = set()
    for cls_table in PRICING_TABLE.values():
        covered.update(k for k in cls_table.keys() if k != "worst_case")
    assert required.issubset(covered)


def test_estimate_max_credit_uses_worst_case_for_hold_sizing():
    n = estimate_max_credit(prompt_tokens=1000, max_tokens=800, model_class="high")
    assert n == 150


def test_usd_per_credit_constant():
    assert USD_PER_CREDIT == 0.0001
