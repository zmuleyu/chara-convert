def test_platforms_returns_sources_and_targets(client):
    res = client.get("/api/platforms")
    assert res.status_code == 200
    body = res.json()
    assert "sources" in body and "targets" in body
    assert len(body["sources"]) >= 6
    assert len(body["targets"]) >= 6
    for entry in body["sources"]:
        assert {"slug", "name", "kind"} <= set(entry)
        assert entry["kind"] in {"file", "paste"}
    for entry in body["targets"]:
        assert {"slug", "name"} <= set(entry)


def test_paste_platforms_include_known_three(client):
    body = client.get("/api/platforms").json()
    paste_slugs = {e["slug"] for e in body["sources"] if e["kind"] == "paste"}
    # NOTE: real slugs from CAIParser/ChaiParser/PolyBuzzParser
    assert {"character_ai", "chai", "polybuzz"} <= paste_slugs
