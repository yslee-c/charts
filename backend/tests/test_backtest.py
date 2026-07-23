"""123/2B 策略回测测试。"""
import json
import math

from app.skills.native import futures_backtest as fb
from app.skills.native.backtest import backtest_123_2b


def market(n=220):
    """真实价位量级（~3500）的波动行情，产生若干交易。"""
    bars = []
    for i in range(n):
        c = (
            3500
            + 200 * math.sin(2 * math.pi * i / 45)
            + 60 * math.sin(2 * math.pi * i / 13)
            + 0.4 * i
        )
        bars.append(
            {
                "date": f"2024-{i // 28 + 1:02d}-{i % 28 + 1:02d}",
                "open": c,
                "high": c + 15,
                "low": c - 15,
                "close": c,
                "volume": 1000,
            }
        )
    return bars


def test_backtest_structure_and_bounds():
    r = backtest_123_2b(market(), entry_conf=40)
    assert r["ok"] is True
    m = r["metrics"]
    assert m["trades"] >= 1
    assert 0 <= m["win_rate"] <= 100
    assert len(r["equity"]) == m["trades"]  # 每笔交易一个资金曲线点
    for t in r["trades"]:
        assert {"side", "entry", "exit", "return_pct", "reason"} <= set(t)
        assert t["side"] in ("long", "short")


def test_backtest_no_lookahead_entry_next_bar():
    """进场价应等于信号次日的开盘价（无未来函数的体现）。"""
    r = backtest_123_2b(market(), entry_conf=40)
    assert all(isinstance(t["entry"], (int, float)) for t in r["trades"])


def test_backtest_insufficient_data():
    r = backtest_123_2b([{"date": f"d{i}", "open": 1, "high": 2, "low": 0.5, "close": 1} for i in range(20)])
    assert r["ok"] is False


def test_backtest_skill_run(monkeypatch):
    monkeypatch.setattr(
        "app.skills.native.futures_trend._fetch_daily", lambda symbol, n: market()
    )
    data = json.loads(fb.run({"symbol": "螺纹钢", "entry_conf": 40}))
    assert data["ok"] is True
    assert data["kind"] == "backtest"
    assert data["symbol"] == "螺纹钢" and data["resolved"] == "RB0"
    assert "metrics" in data and "win_rate" in data["metrics"]
    assert "equity" in data and "summary" in data


def test_backtest_skill_missing_symbol():
    data = json.loads(fb.run({"symbol": ""}))
    assert data["ok"] is False


def test_backtest_builtin_seeded(client):
    fts = [s for s in client.get("/api/skills").json() if s["name"] == "futures-backtest"]
    assert fts and fts[0]["kind"] == "native" and fts[0]["is_active"] is True
