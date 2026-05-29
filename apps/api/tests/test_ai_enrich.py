import os


def test_ai_enrich_mock_streams_chunks(client, monkeypatch):
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "Aerin is calm and quietly observant.")
    body = {
        "card": {"name": "Aerin", "description": "wandering mage"},
        "field": "personality",
    }
    with client.stream("POST", "/api/ai/enrich", json=body) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        chunks = [line for line in res.iter_lines() if line.startswith("data:")]
    text = "".join(c.removeprefix("data:").strip() for c in chunks)
    assert "Aerin" in text


def test_ai_enrich_422_on_unknown_field(client):
    res = client.post("/api/ai/enrich", json={"card": {}, "field": "wat"})
    assert res.status_code == 422


def test_ai_enrich_ignores_unknown_card_keys(client, monkeypatch):
    """Regression: frontend merges sourceCard + converted + overrides into the
    card dict; extra keys like 'appearance' or layer-flattened fields must not
    crash NormalizedCard construction. first_message → first_mes alias too."""
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "calm and quietly observant")
    body = {
        "card": {
            "name": "Aerin",
            "description": "wandering mage",
            "first_message": "Hello, traveler.",
            "appearance": "tall, dark hair",
            "vibes_layer": "moody",
            "ready_score": 42,
        },
        "field": "personality",
    }
    with client.stream("POST", "/api/ai/enrich", json=body) as res:
        assert res.status_code == 200
        chunks = [line for line in res.iter_lines() if line.startswith("data:")]
    text = "".join(c.removeprefix("data:").strip() for c in chunks)
    assert "calm" in text
