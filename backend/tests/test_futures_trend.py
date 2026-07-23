"""期货 123/2B 分析（ATR/ZigZag/时序/置信度）+ 清洗/映射/结构化 + native 守卫。"""
import json
import math

from app.skills.native import futures_trend as ft
from app.skills.native.futures_trend import (
    analyze_123_2b,
    clean_bars,
    format_analysis,
    _atr,
    _zigzag,
)
from app.skills.native.symbols import resolve_symbol
from app.skills.parser import parse_skill_md


def _bar(i, c):
    return {
        "date": f"2024-{i // 28 + 1:02d}-{i % 28 + 1:02d}",
        "open": c,
        "high": c + 2,
        "low": c - 2,
        "close": c,
        "volume": 1000,
    }


def clean_uptrend(n=60):
    """缓升 + 大幅摆动（回调深度 > 2×ATR，ZigZag 可识别）。"""
    return [_bar(i, 100 + 0.4 * i + 12 * math.sin(2 * math.pi * i / 14)) for i in range(n)]


def topping(n=56):
    """先涨到 i=32 见顶再跌，制造见顶反转（收在下行段）。"""
    bars = []
    for i in range(n):
        base = 100 + 0.9 * i if i <= 32 else 100 + 0.9 * 32 - 1.6 * (i - 32)
        bars.append(_bar(i, base + 12 * math.sin(2 * math.pi * i / 14)))
    return bars


def bottoming(n=56):
    """先跌到 i=32 见底再涨，制造见底反转（收在上行段）。"""
    bars = []
    for i in range(n):
        base = 200 - 0.9 * i if i <= 32 else 200 - 0.9 * 32 + 1.6 * (i - 32)
        bars.append(_bar(i, base + 12 * math.sin(2 * math.pi * i / 14)))
    return bars


def test_atr_and_zigzag_basic():
    bars = clean_uptrend()
    atr = _atr(bars)
    assert atr > 0
    piv = _zigzag(bars, 2.0 * atr)
    kinds = [k for _, _, k in piv]
    # 交替出现高低点
    assert "H" in kinds and "L" in kinds
    for a, b in zip(kinds, kinds[1:]):
        assert a != b


def test_clean_uptrend_up_and_low_bear_confidence():
    a = analyze_123_2b(clean_uptrend())
    assert a["ok"] is True
    assert a["trend"] == "up"
    assert 0 <= a["bearish"]["confidence"] <= 100
    # 上升趋势里，看跌置信度不应很高
    assert a["bearish"]["confidence"] < 50


def test_topping_triggers_bearish():
    a = analyze_123_2b(topping())
    assert a["ok"] is True
    assert a["trend"] in ("down", "range")
    # 见顶反转：看跌应有信号且置信度高于看涨
    assert a["bearish"]["count"] >= 1
    assert a["bearish"]["confidence"] >= a["bullish"]["confidence"]


def test_bottoming_triggers_bullish():
    a = analyze_123_2b(bottoming())
    assert a["ok"] is True
    assert a["trend"] in ("up", "range")
    assert a["bullish"]["count"] >= 1
    assert a["bullish"]["confidence"] >= a["bearish"]["confidence"]


def test_confidence_bounds():
    a = analyze_123_2b(topping())
    for side in ("bearish", "bullish"):
        assert 0 <= a["confidence"][side] <= 100


def test_insufficient_data():
    a = analyze_123_2b([_bar(i, 100 + i) for i in range(10)])
    assert a["ok"] is False


def test_format_contains_key_fields():
    a = analyze_123_2b(topping())
    text = format_analysis("RB0", topping(), a)
    assert "RB0" in text and "趋势" in text and "置信度" in text


def test_resolve_symbol():
    assert resolve_symbol("沪锡") == "SN0"
    assert resolve_symbol("螺纹钢") == "RB0"
    assert resolve_symbol("沪锡主连") == "SN0"
    assert resolve_symbol("rb2410") == "RB2410"
    assert resolve_symbol("SN0") == "SN0"


def test_clean_bars_sort_dedup_drop_gap():
    raw = [
        {"date": "2024-01-03", "open": 12, "high": 13, "low": 11, "close": 12},
        {"date": "2024-01-01", "open": 10, "high": 11, "low": 9, "close": 10},
        {"date": "2024-01-02", "open": 10.5, "high": 12, "low": 10, "close": 11},
        {"date": "2024-01-02", "open": 10.6, "high": 12, "low": 10, "close": 11.2},
        {"date": "2024-01-04", "open": -1, "high": 0, "low": 0, "close": 0},
        {"date": "2024-01-05", "open": 30, "high": 31, "low": 29, "close": 30},
    ]
    clean, notes = clean_bars(raw)
    assert [b["date"] for b in clean] == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
        "2024-01-05",
    ]
    assert clean[1]["close"] == 11.2
    assert any("异常" in n for n in notes)
    assert any("跳空" in n for n in notes)


def test_run_returns_structured_json(monkeypatch):
    monkeypatch.setattr(ft, "_fetch_daily", lambda symbol, n: clean_uptrend())
    data = json.loads(ft.run({"symbol": "沪锡"}))
    assert data["ok"] is True
    assert data["symbol"] == "沪锡" and data["resolved"] == "SN0"
    assert data["trend"] == "up"
    assert "confidence" in data and "atr" in data
    assert len(data["bearish"]["conditions"]) == 3
    assert all("met" in c and "label" in c for c in data["bearish"]["conditions"])
    assert isinstance(data["series"], list) and len(data["series"]) > 0
    assert "summary" in data


def test_run_missing_symbol():
    data = json.loads(ft.run({"symbol": ""}))
    assert data["ok"] is False and "请提供" in data["summary"]


def test_parser_accepts_native():
    md = (
        "---\nname: futures-trend\ndescription: 分析期货走势\nkind: native\n"
        "parameters:\n  type: object\n  properties:\n    symbol: {type: string}\n"
        "  required: [symbol]\n---\n\n# 正文\n分析。"
    )
    f = parse_skill_md(md)
    assert f["kind"] == "native"
    assert f["http_action"] is None


def test_user_cannot_create_native(client):
    native_md = "---\nname: hacky\ndescription: x\nkind: native\n---\n\nbody"
    assert client.post("/api/skills/import", json={"content": native_md}).status_code == 400
    assert (
        client.post(
            "/api/skills",
            json={"name": "hacky2", "description": "x", "kind": "native"},
        ).status_code
        == 422
    )


def test_native_builtin_seeded(client):
    fts = [s for s in client.get("/api/skills").json() if s["name"] == "futures-trend"]
    assert fts and fts[0]["kind"] == "native" and fts[0]["is_active"] is True
