from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_paste_detects_cai(client):
    raw = (FIXTURES / "cai_sample.txt").read_text()
    res = client.post("/api/parse", json={"raw": raw, "kind": "paste"})
    assert res.status_code == 200
    body = res.json()
    assert body["detectedPlatform"] == "character_ai"
    assert body["confidence"] > 0.5
    assert body["card"]["name"] == "Aerin"


def test_parse_file_json_sillytavern(client):
    blob = (FIXTURES / "sillytavern_sample.json").read_bytes()
    res = client.post(
        "/api/parse",
        files={"file": ("card.json", blob, "application/json")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["detectedPlatform"] == "sillytavern_v2"
    assert body["card"]["name"] == "Aerin"


def test_parse_returns_422_on_empty_paste(client):
    res = client.post("/api/parse", json={"raw": "", "kind": "paste"})
    assert res.status_code == 422
