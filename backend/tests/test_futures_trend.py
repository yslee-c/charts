"""期货 123/2B 分析（纯逻辑）+ 清洗/映射/结构化输出 + native 守卫测试。"""
import json

from app.skills.native import futures_trend as ft
from app.skills.native.futures_trend import analyze_123_2b, clean_bars, format_analysis
from app.skills.native.symbols import resolve_symbol
from app.skills.parser import parse_skill_md


def bars_of(highs, lows, closes):
    return [
        {"date": f"d{i}", "open": c, "high": h, "low": lo, "close": c}
        for i, (h, lo, c) in enumerate(zip(highs, lows, closes))
    ]


# 清晰上升趋势：更高的高点 + 更高的低点，无反转
UPTREND = bars_of(
    highs=[10, 12, 11, 14, 13, 16, 15, 18, 17],
    lows=[8, 9, 8.5, 10, 9.5, 12, 11, 14, 13],
    closes=[9, 11, 10, 13, 12, 15, 14, 17, 16],
)

# 见顶反转：创新高后回落（2B 顶），并跌破前期回调低点（123 的 ①③）
TOP = bars_of(
    highs=[18, 20, 19, 23, 20, 19, 18],
    lows=[15, 16, 14, 18, 15, 17, 13],
    closes=[16, 19, 15, 22, 16, 18, 13],
)


def test_clean_uptrend_no_reversal():
    a = analyze_123_2b(UPTREND, window=1)
    assert a["ok"] is True
    assert a["trend"] == "up"
    assert a["bearish"]["count"] == 0
    assert a["bearish"]["twoB"] is False


def test_top_reversal_123_and_2b():
    a = analyze_123_2b(TOP, window=1)
    assert a["ok"] is True
    assert a["trend"] == "up"           # 反转尚未改变主要结构，但出现见顶信号
    assert a["bearish"]["count"] == 2   # ① 跌破趋势线 + ③ 跌破前低
    assert a["bearish"]["twoB"] is True
    conds = "".join(a["bearish"]["conditions"])
    assert "③" in conds and "②" not in conds


def test_insufficient_data():
    a = analyze_123_2b(bars_of([1, 2, 3], [0, 1, 2], [1, 2, 3]), window=1)
    assert a["ok"] is False


def test_format_contains_key_fields():
    a = analyze_123_2b(TOP, window=1)
    text = format_analysis("RB0", TOP, a)
    assert "RB0" in text
    assert "趋势" in text
    assert "2B" in text


def test_parser_accepts_native():
    md = (
        "---\nname: futures-trend\ndescription: 分析期货走势\nkind: native\n"
        "parameters:\n  type: object\n  properties:\n    symbol: {type: string}\n"
        "  required: [symbol]\n---\n\n# 正文\n分析。"
    )
    f = parse_skill_md(md)
    assert f["kind"] == "native"
    assert f["http_action"] is None
    assert f["parameters_schema"]["required"] == ["symbol"]


def test_user_cannot_create_native(client):
    native_md = "---\nname: hacky\ndescription: x\nkind: native\n---\n\nbody"
    assert client.post("/api/skills/import", json={"content": native_md}).status_code == 400
    # 结构化创建根本不接受 native（schema 限制）
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


def test_resolve_symbol():
    assert resolve_symbol("沪锡") == "SN0"
    assert resolve_symbol("螺纹钢") == "RB0"
    assert resolve_symbol("沪锡主连") == "SN0"
    assert resolve_symbol("rb2410") == "RB2410"   # 代码原样大写
    assert resolve_symbol("SN0") == "SN0"


def test_clean_bars_sort_dedup_drop_gap():
    raw = [
        {"date": "2024-01-03", "open": 12, "high": 13, "low": 11, "close": 12},
        {"date": "2024-01-01", "open": 10, "high": 11, "low": 9, "close": 10},
        {"date": "2024-01-02", "open": 10.5, "high": 12, "low": 10, "close": 11},
        {"date": "2024-01-02", "open": 10.6, "high": 12, "low": 10, "close": 11.2},  # 同日重复
        {"date": "2024-01-04", "open": -1, "high": 0, "low": 0, "close": 0},  # 非法
        {"date": "2024-01-05", "open": 30, "high": 31, "low": 29, "close": 30},  # 相对前收 ~11 跳空
    ]
    clean, notes = clean_bars(raw)
    dates = [b["date"] for b in clean]
    assert dates == ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-05"]  # 排序+去重+剔非法
    assert clean[1]["close"] == 11.2  # 去重保留后一条
    assert any("异常" in n for n in notes)
    assert any("跳空" in n for n in notes)


def _sine_uptrend(n=48, trend=0.6, amp=8.0, period=12):
    """带上升趋势的正弦波，摆动明显、适合 window=3 识别枢轴。"""
    import math

    bars = []
    for i in range(n):
        c = 100 + trend * i + amp * math.sin(2 * math.pi * i / period)
        bars.append(
            {
                "date": f"2024-{i // 20 + 1:02d}-{i % 20 + 1:02d}",
                "open": c,
                "high": c + 1,
                "low": c - 1,
                "close": c,
            }
        )
    return bars


def test_run_returns_structured_json(monkeypatch):
    """把 _fetch_daily 换成合成数据，验证 run() 输出的结构化 JSON。"""
    monkeypatch.setattr(ft, "_fetch_daily", lambda symbol, n: _sine_uptrend())
    out = ft.run({"symbol": "沪锡"})
    data = json.loads(out)
    assert data["ok"] is True
    assert data["symbol"] == "沪锡" and data["resolved"] == "SN0"
    assert data["trend"] == "up"
    assert set(data["pivots"].keys()) == {"highs", "lows"}
    assert len(data["bearish"]["conditions"]) == 3  # 三条都带 met 布尔
    assert all("met" in c and "label" in c for c in data["bearish"]["conditions"])
    assert data["stops"]["short_ref"] is not None
    assert isinstance(data["series"], list) and len(data["series"]) > 0
    assert "summary" in data


def test_run_missing_symbol():
    data = json.loads(ft.run({"symbol": ""}))
    assert data["ok"] is False and "请提供" in data["summary"]
