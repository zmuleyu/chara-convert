def test_openrouter_takes_precedence_over_anthropic(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **_: object())

    from chara_convert.llm.factory import build_ai_client_or_none
    client, status = build_ai_client_or_none()
    assert status == "openrouter"
    from chara_convert.llm.openrouter import OpenRouterClient
    assert isinstance(client, OpenRouterClient)


def test_mock_still_wins_over_openrouter(monkeypatch):
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    from chara_convert.llm.factory import build_ai_client_or_none
    _, status = build_ai_client_or_none()
    assert status == "mock"


def test_legacy_anthropic_still_works_when_no_or_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **_: object())
    from chara_convert.llm.factory import build_ai_client_or_none
    _, status = build_ai_client_or_none()
    assert status == "anthropic"
