"""期货 123/2B 分析（纯逻辑）+ native 守卫测试。"""
from app.skills.native.futures_trend import analyze_123_2b, format_analysis
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
    ft = [s for s in client.get("/api/skills").json() if s["name"] == "futures-trend"]
    assert ft and ft[0]["kind"] == "native" and ft[0]["is_active"] is True
