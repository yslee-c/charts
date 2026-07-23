"""会话 CRUD API 测试。"""
from tests.fakes import EchoLLM, drain_sse


def _new_conversation(client, monkeypatch, message="你好"):
    monkeypatch.setattr("app.agent.orchestrator.get_llm_client", lambda: EchoLLM())
    with client.stream("POST", "/api/chat", json={"message": message}) as r:
        evs = drain_sse(r)
    return next(e["conversation"]["id"] for e in evs if "conversation" in e)


def test_list_and_detail(client, monkeypatch):
    cid = _new_conversation(client, monkeypatch, "第一次对话")
    lst = client.get("/api/conversations").json()
    assert any(c["id"] == cid for c in lst)
    detail = client.get(f"/api/conversations/{cid}").json()
    assert detail["messages"][0]["content"] == "第一次对话"


def test_title_from_first_message(client, monkeypatch):
    cid = _new_conversation(client, monkeypatch, "帮我写一封邮件")
    title = client.get(f"/api/conversations/{cid}").json()["title"]
    assert "帮我写一封邮件" in title


def test_rename(client, monkeypatch):
    cid = _new_conversation(client, monkeypatch)
    r = client.patch(f"/api/conversations/{cid}", json={"title": "改名了"})
    assert r.status_code == 200 and r.json()["title"] == "改名了"


def test_delete(client, monkeypatch):
    cid = _new_conversation(client, monkeypatch)
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404


def test_missing_404(client):
    assert client.get("/api/conversations/9999").status_code == 404
    assert client.patch("/api/conversations/9999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/conversations/9999").status_code == 404
