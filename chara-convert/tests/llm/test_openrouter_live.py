import os

import pytest

pytestmark = pytest.mark.live_smoke


@pytest.mark.skipif(os.environ.get("RUN_OR_SMOKE") != "1", reason="set RUN_OR_SMOKE=1 to run")
def test_real_or_low_class_returns_text_within_budget():
    from chara_convert.llm.openrouter import OpenRouterClient
    c = OpenRouterClient(model_class="low")
    out = c.complete("Say hello in three words.", max_tokens=20, temperature=0.1)
    assert isinstance(out, str)
    assert len(out) > 0
