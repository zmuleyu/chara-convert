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
