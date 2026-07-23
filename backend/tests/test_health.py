def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "health" in r.json()
