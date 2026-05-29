import pytest

from chara_convert.llm.router import (
    InsufficientCreditForAnyClass,
    pick_model_class,
    plan_request,
)


@pytest.mark.parametrize("balance,low,high,expected", [
    (10000, 150, 50, "high"),
    (100,   50, 150, "low"),
    (50,    50, 150, "low"),
    (49,    50, 150, None),
])
def test_pick_model_class(balance, low, high, expected):
    if expected is None:
        with pytest.raises(InsufficientCreditForAnyClass):
            pick_model_class(balance=balance, est_low=low, est_high=high)
    else:
        assert pick_model_class(balance=balance, est_low=low, est_high=high) == expected


def test_plan_request_returns_chosen_class_and_hold_amount():
    plan = plan_request(
        balance=1000,
        prompt_tokens=500, max_tokens=400,
    )
    # high worst-case rates {"input":3.00,"output":15.00} per 1M tokens →
    # (500*3 + 400*15)/1e6 = 0.0075 USD → ceil(0.0075/0.0001) = 75 credit.
    assert plan["model_class"] == "high"
    assert plan["hold_amount"] == 75


def test_plan_request_falls_back_to_low_when_balance_only_covers_low():
    plan = plan_request(balance=50, prompt_tokens=500, max_tokens=400)
    assert plan["model_class"] == "low"
    assert plan["hold_amount"] == 13
