"""Model-class selection and request planning.

The router is the pure-logic layer between the API route and the OR client.
It decides:
  1. Which model class the user can afford (high > low > 402).
  2. The hold amount (worst-case per class).

It does not touch HTTP, credit, or the OR client directly.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from chara_convert.llm.pricing import estimate_max_credit

ModelClass = Literal["low", "high"]


class InsufficientCreditForAnyClass(RuntimeError):
    """Balance < estimated_low. Surface as 402 at the route boundary."""


class RequestPlan(TypedDict):
    model_class: ModelClass
    hold_amount: int


def pick_model_class(*, balance: int, est_low: int, est_high: int) -> ModelClass:
    if balance >= est_high:
        return "high"
    if balance >= est_low:
        return "low"
    raise InsufficientCreditForAnyClass()


def plan_request(*, balance: int, prompt_tokens: int, max_tokens: int) -> RequestPlan:
    est_low = estimate_max_credit(
        prompt_tokens=prompt_tokens, max_tokens=max_tokens, model_class="low",
    )
    est_high = estimate_max_credit(
        prompt_tokens=prompt_tokens, max_tokens=max_tokens, model_class="high",
    )
    cls = pick_model_class(balance=balance, est_low=est_low, est_high=est_high)
    hold_amount = est_high if cls == "high" else est_low
    return {"model_class": cls, "hold_amount": hold_amount}
