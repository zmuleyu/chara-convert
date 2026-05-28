def test_convert_cai_to_fictionlab(client):
    card = {
        "name": "Aerin",
        "description": "A wandering mage.",
        "personality": "calm, observant",
        "scenario": "Eastern peaks at dawn.",
        "first_message": "Hi there, traveler.",
    }
    res = client.post("/api/convert", json={"card": card, "targetSlug": "fictionlab"})
    assert res.status_code == 200
    body = res.json()
    assert "converted" in body and "gap" in body
    assert isinstance(body["gap"]["ready_score"], (int, float))
    assert 0 <= body["gap"]["ready_score"] <= 100


def test_convert_unknown_target_returns_404(client):
    res = client.post("/api/convert", json={"card": {"name": "x"}, "targetSlug": "nope"})
    assert res.status_code == 404
