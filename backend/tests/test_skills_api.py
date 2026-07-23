"""Skills API 测试（client 已植入 3 个内置 skill）。"""

GREETER = """\
---
name: greeter
description: 打招呼
---

# 问候
说你好。
"""


def _id_of(client, name):
    return next(s["id"] for s in client.get("/api/skills").json() if s["name"] == name)


def test_list_builtins(client):
    names = {s["name"] for s in client.get("/api/skills").json()}
    assert {"wenyanwen", "emoji-tldr", "ip-geo"} <= names


def test_active_only_filter(client):
    active = {s["name"] for s in client.get("/api/skills?active_only=true").json()}
    assert "ip-geo" not in active  # 默认停用
    assert "wenyanwen" in active


def test_structured_create_dup_and_bad_name(client):
    payload = {"name": "my-tool", "description": "d", "kind": "instruction"}
    assert client.post("/api/skills", json=payload).status_code == 201
    assert client.post("/api/skills", json=payload).status_code == 409  # 重名
    bad = {"name": "Bad Name", "description": "d"}
    assert client.post("/api/skills", json=bad).status_code == 422  # 名称非法


def test_import_and_versioning(client):
    r = client.post("/api/skills/import", json={"content": GREETER})
    assert r.status_code == 201 and r.json()["version"] == 1
    r2 = client.post("/api/skills/import", json={"content": GREETER})
    assert r2.json()["version"] == 2  # 同名更新
    assert client.post("/api/skills/import", json={"content": "garbage"}).status_code == 422


def test_source_and_put_update(client):
    sid = _id_of(client, "wenyanwen")
    src = client.get(f"/api/skills/{sid}/source").json()["content"]
    assert "name: wenyanwen" in src
    edited = src.replace("# 文言文改写", "# 文言文改写（改）")
    r = client.put(f"/api/skills/{sid}", json={"content": edited})
    assert r.status_code == 200 and r.json()["version"] == 2
    assert "（改）" in r.json()["skill_md"]


def test_put_conflict_and_errors(client):
    sid = _id_of(client, "wenyanwen")
    src = client.get(f"/api/skills/{sid}/source").json()["content"]
    conflict = src.replace("name: wenyanwen", "name: emoji-tldr")
    assert client.put(f"/api/skills/{sid}", json={"content": conflict}).status_code == 409
    assert client.put(f"/api/skills/{sid}", json={"content": "x"}).status_code == 422
    assert client.put("/api/skills/9999", json={"content": src}).status_code == 404


def test_activate_and_delete(client):
    sid = _id_of(client, "ip-geo")
    r = client.patch(f"/api/skills/{sid}/active", json={"is_active": True})
    assert r.json()["is_active"] is True
    assert client.delete(f"/api/skills/{sid}").status_code == 204
    assert client.get(f"/api/skills/{sid}").status_code == 404
