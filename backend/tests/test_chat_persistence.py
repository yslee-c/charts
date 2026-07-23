"""聊天编排 + 会话持久化 + 工具活动 + 审计（用假 LLM）。"""
from tests.fakes import EchoLLM, ToolCallingLLM, drain_sse


def _use_llm(monkeypatch, llm):
    monkeypatch.setattr("app.agent.orchestrator.get_llm_client", lambda: llm)


def test_new_conversation_and_history(client, monkeypatch):
    _use_llm(monkeypatch, EchoLLM("答"))
    with client.stream("POST", "/api/chat", json={"message": "第一句"}) as r:
        evs = drain_sse(r)

    conv = next(e["conversation"] for e in evs if "conversation" in e)
    assert conv["is_new"] is True
    cid = conv["id"]
    answer1 = "".join(e["delta"] for e in evs if "delta" in e)
    assert "第一句" in answer1  # echo 证明历史被加载

    # 第二轮：同一会话
    _use_llm(monkeypatch, EchoLLM("答"))
    with client.stream(
        "POST", "/api/chat", json={"conversation_id": cid, "message": "第二句"}
    ) as r:
        drain_sse(r)

    detail = client.get(f"/api/conversations/{cid}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_missing_conversation_404(client, monkeypatch):
    _use_llm(monkeypatch, EchoLLM())
    with client.stream(
        "POST", "/api/chat", json={"conversation_id": 9999, "message": "x"}
    ) as r:
        assert r.status_code == 404


def test_no_key_returns_503(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "dashscope_api_key", "")
    with client.stream("POST", "/api/chat", json={"message": "x"}) as r:
        assert r.status_code == 503


def test_tool_call_persists_activity_and_audit(client, monkeypatch):
    _use_llm(monkeypatch, ToolCallingLLM("wenyanwen", answer="改写好了"))
    with client.stream("POST", "/api/chat", json={"message": "把「你好」改文言"}) as r:
        evs = drain_sse(r)

    assert [e["tool_call"]["skill"] for e in evs if "tool_call" in e] == ["wenyanwen"]
    assert any(e.get("tool_result", {}).get("ok") for e in evs)

    cid = next(e["conversation"]["id"] for e in evs if "conversation" in e)
    # 会话消息顺序：user → activity → assistant
    roles = [m["role"] for m in client.get(f"/api/conversations/{cid}").json()["messages"]]
    assert roles == ["user", "activity", "assistant"]

    # 审计记录里有这次 wenyanwen 调用
    runs = client.get("/api/skill-runs").json()
    assert any(x["skill_name"] == "wenyanwen" and x["status"] == "ok" for x in runs)


def test_skill_runs_empty_initially(client):
    assert client.get("/api/skill-runs").json() == []
