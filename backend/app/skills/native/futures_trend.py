"""内置 native skill：期货趋势分析（123 法则 / 2B 法则）。

- 用 akshare 拉取期货日 K（惰性导入，未安装/无网络时优雅报错）。
- analyze_123_2b 为纯函数，可脱离网络单测。

法则（Victor Sperandeo）：
  123（自上升趋势见顶）：① 跌破上升趋势线 ② 反弹未创新高 ③ 跌破前期回调低点
  2B：创新高后无法站稳、回落到前高之下（顶部假突破）；底部镜像。
"""
import json

from app.skills.native.symbols import resolve_symbol

Bar = dict  # {"date","open","high","low","close"}


# ----------------------------- 纯分析逻辑 -----------------------------

def _pivots(bars: list[Bar], w: int) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """用左右各 w 根的窗口找摆动高/低点，返回 (highs, lows) 的 (index, price) 列表。"""
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    n = len(bars)
    for i in range(w, n - w):
        window = bars[i - w : i + w + 1]
        hi, lo = bars[i]["high"], bars[i]["low"]
        if (
            hi >= max(b["high"] for b in window)
            and hi > bars[i - 1]["high"]
            and hi > bars[i + 1]["high"]
        ):
            highs.append((i, hi))
        if (
            lo <= min(b["low"] for b in window)
            and lo < bars[i - 1]["low"]
            and lo < bars[i + 1]["low"]
        ):
            lows.append((i, lo))
    return highs, lows


def _trendline(p1: tuple[int, float], p2: tuple[int, float], x: int) -> float:
    """过两个摆动点的直线在 x 处的取值。"""
    (i1, v1), (i2, v2) = p1, p2
    if i2 == i1:
        return v2
    return v2 + (v2 - v1) / (i2 - i1) * (x - i2)


def analyze_123_2b(bars: list[Bar], window: int = 3) -> dict:
    """对日 K 序列做 123 / 2B 判别。纯函数，无副作用。"""
    n = len(bars)
    if n < 2 * window + 3:
        return {"ok": False, "reason": f"数据不足（{n} 根）"}

    highs, lows = _pivots(bars, window)
    if len(highs) < 2 or len(lows) < 2:
        return {"ok": False, "reason": "摆动高/低点不足，无法判别（可尝试更长周期或更多数据）"}

    last = bars[-1]["close"]
    x = n - 1
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    lh = highs[-1][1] < highs[-2][1]
    ll = lows[-1][1] < lows[-2][1]
    if hh and hl:
        trend = "up"
    elif lh and ll:
        trend = "down"
    else:
        trend = "range"

    # 看跌反转（自上升趋势）
    bear_c1 = last < _trendline(lows[-2], lows[-1], x)
    bear_c2 = highs[-1][1] <= highs[-2][1]
    bear_c3 = last < lows[-1][1]
    bear_2b = (highs[-1][1] > highs[-2][1]) and (last < highs[-2][1])
    bear = []
    if bear_c1:
        bear.append("① 跌破上升趋势线")
    if bear_c2:
        bear.append("② 反弹未创新高")
    if bear_c3:
        bear.append("③ 跌破前期回调低点")

    # 看涨反转（自下降趋势）
    bull_c1 = last > _trendline(highs[-2], highs[-1], x)
    bull_c2 = lows[-1][1] >= lows[-2][1]
    bull_c3 = last > highs[-1][1]
    bull_2b = (lows[-1][1] < lows[-2][1]) and (last > lows[-2][1])
    bull = []
    if bull_c1:
        bull.append("① 突破下降趋势线")
    if bull_c2:
        bull.append("② 回落未创新低")
    if bull_c3:
        bull.append("③ 突破前期反弹高点")

    return {
        "ok": True,
        "trend": trend,
        "last_close": last,
        "pivot_highs": highs[-2:],
        "pivot_lows": lows[-2:],
        "bearish": {
            "conditions": bear,
            "count": len(bear),
            "twoB": bear_2b,
            "c1": bear_c1,
            "c2": bear_c2,
            "c3": bear_c3,
        },
        "bullish": {
            "conditions": bull,
            "count": len(bull),
            "twoB": bull_2b,
            "c1": bull_c1,
            "c2": bull_c2,
            "c3": bull_c3,
        },
    }


_TREND_CN = {"up": "上升", "down": "下降", "range": "盘整/震荡"}


def format_analysis(symbol: str, bars: list[Bar], a: dict) -> str:
    if not a["ok"]:
        return f"{symbol}：{a['reason']}"

    highs = [round(p, 2) for _, p in a["pivot_highs"]]
    lows = [round(p, 2) for _, p in a["pivot_lows"]]
    bear, bull = a["bearish"], a["bullish"]

    lines = [
        f"品种 {symbol} —— 最近 {len(bars)} 根日K（截至 {bars[-1]['date']}）",
        f"当前趋势：{_TREND_CN[a['trend']]}，最新收盘 {a['last_close']}",
        f"最近摆动高点：{highs}；摆动低点：{lows}",
        f"看跌 123 满足 {bear['count']}/3：{'、'.join(bear['conditions']) or '无'}"
        + ("；⚠ 出现 2B 顶部假突破" if bear["twoB"] else ""),
        f"看涨 123 满足 {bull['count']}/3：{'、'.join(bull['conditions']) or '无'}"
        + ("；⚠ 出现 2B 底部假突破" if bull["twoB"] else ""),
    ]

    # 参考结论（agent 会据此展开叙述）
    if a["trend"] == "up" and (bear["count"] >= 2 or bear["twoB"]):
        lines.append("参考结论：上升趋势出现见顶信号，警惕反转；空头参考止损可放最近摆动高点上方。")
    elif a["trend"] == "down" and (bull["count"] >= 2 or bull["twoB"]):
        lines.append("参考结论：下降趋势出现见底信号，关注反转；多头参考止损可放最近摆动低点下方。")
    else:
        lines.append("参考结论：暂无明确的 123/2B 反转确认，趋势延续或盘整为主。")
    return "\n".join(lines)


# ----------------------------- 数据拉取 -----------------------------

_COLS = {
    "date": ["date", "日期", "时间"],
    "open": ["open", "开盘价", "开盘"],
    "high": ["high", "最高价", "最高"],
    "low": ["low", "最低价", "最低"],
    "close": ["close", "收盘价", "收盘"],
}


def _bars_from_df(df, n: int) -> list[Bar]:
    cols = list(df.columns)

    def find(keys):
        for k in keys:
            if k in cols:
                return k
        return None

    mapping = {f: find(ks) for f, ks in _COLS.items()}
    missing = [f for f in ("open", "high", "low", "close") if mapping[f] is None]
    if missing:
        raise RuntimeError(f"无法识别行情数据列，缺 {missing}；实际列：{cols}")

    tail = df.tail(n)
    bars: list[Bar] = []
    for _, row in tail.iterrows():
        bars.append(
            {
                "date": str(row[mapping["date"]]) if mapping["date"] else "",
                "open": float(row[mapping["open"]]),
                "high": float(row[mapping["high"]]),
                "low": float(row[mapping["low"]]),
                "close": float(row[mapping["close"]]),
            }
        )
    return bars


_GAP_THRESHOLD = 0.08  # 相邻两日开盘 vs 前收盘跳空超过 8% 视为异常/换月


def clean_bars(bars: list[Bar]) -> tuple[list[Bar], list[str]]:
    """清洗：按日期排序、按日期去重、剔除非法 OHLC、标注大跳空。

    返回 (clean_bars, notes)。纯函数，可单测。
    """
    notes: list[str] = []

    # 排序 + 去重（同日保留最后一条）
    by_date: dict[str, Bar] = {}
    for b in sorted(bars, key=lambda x: str(x.get("date", ""))):
        by_date[str(b.get("date", ""))] = b
    ordered = [by_date[d] for d in sorted(by_date)]

    # 剔除非法：非正、NaN、high<low
    clean: list[Bar] = []
    dropped = 0
    for b in ordered:
        try:
            o, h, low, c = (
                float(b["open"]),
                float(b["high"]),
                float(b["low"]),
                float(b["close"]),
            )
        except (KeyError, TypeError, ValueError):
            dropped += 1
            continue
        vals = [o, h, low, c]
        if any(v <= 0 or v != v for v in vals) or h < low:  # v!=v 判 NaN
            dropped += 1
            continue
        clean.append(b)
    if dropped:
        notes.append(f"剔除 {dropped} 根异常/缺失数据")

    # 跳空标注
    gaps = 0
    for prev, cur in zip(clean, clean[1:]):
        pc = float(prev["close"])
        if pc > 0 and abs(float(cur["open"]) - pc) / pc > _GAP_THRESHOLD:
            gaps += 1
    if gaps:
        notes.append(
            f"检测到 {gaps} 处较大跳空（>8%），主力连续合约可能含换月跳空，趋势线仅供参考"
        )

    return clean, notes


def _fetch_daily(symbol: str, n: int) -> list[Bar]:
    """用 akshare 拉取期货日 K；主连（如 RB0）优先走 futures_main_sina。"""
    import akshare as ak  # 惰性导入：未安装时抛 ImportError，由 run() 捕获

    errors = []
    df = None
    try:
        df = ak.futures_main_sina(symbol=symbol.upper())
    except Exception as exc:  # noqa: BLE001
        errors.append(f"futures_main_sina: {exc}")
    if df is None or len(df) == 0:
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol.lower())
        except Exception as exc:  # noqa: BLE001
            errors.append(f"futures_zh_daily_sina: {exc}")
    if df is None or len(df) == 0:
        raise RuntimeError("；".join(errors) or "无数据返回")
    return _bars_from_df(df, n)


# ----------------------------- 结构化结果 -----------------------------

_BEAR_LABEL = {"①": "跌破上升趋势线", "②": "反弹未创新高", "③": "跌破前期回调低点"}
_BULL_LABEL = {"①": "突破下降趋势线", "②": "回落未创新低", "③": "突破前期反弹高点"}


def _conditions(flags: dict, labels: dict) -> list[dict]:
    return [
        {"code": code, "label": labels[code], "met": flags[key]}
        for code, key in (("①", "c1"), ("②", "c2"), ("③", "c3"))
    ]


def _build_result(
    original: str, resolved: str, bars: list[Bar], analysis: dict, notes: list[str]
) -> dict:
    label = f"{original}（{resolved}）"
    if not analysis["ok"]:
        return {
            "ok": False,
            "symbol": original,
            "resolved": resolved,
            "summary": f"{label}：{analysis['reason']}",
        }

    def point(p):
        i, price = p
        return {"i": i, "date": bars[i]["date"], "price": round(price, 2)}

    highs = [point(p) for p in analysis["pivot_highs"]]
    lows = [point(p) for p in analysis["pivot_lows"]]
    bear, bull = analysis["bearish"], analysis["bullish"]

    return {
        "ok": True,
        "symbol": original,
        "resolved": resolved,
        "as_of": bars[-1]["date"],
        "bars_count": len(bars),
        "trend": analysis["trend"],
        "last_close": round(analysis["last_close"], 2),
        "pivots": {"highs": highs, "lows": lows},
        "bearish": {
            "count": bear["count"],
            "twoB": bear["twoB"],
            "conditions": _conditions(bear, _BEAR_LABEL),
        },
        "bullish": {
            "count": bull["count"],
            "twoB": bull["twoB"],
            "conditions": _conditions(bull, _BULL_LABEL),
        },
        "stops": {
            "short_ref": highs[-1]["price"] if highs else None,
            "long_ref": lows[-1]["price"] if lows else None,
        },
        "notes": notes,
        # 供前端画价格线（最近 60 根 [日期, 收盘]）
        "series": [[b["date"], round(float(b["close"]), 2)] for b in bars[-60:]],
        "summary": format_analysis(label, bars, analysis),
    }


# ----------------------------- handler 入口 -----------------------------

def run(arguments: dict) -> str:
    """返回结构化 JSON 字符串：既供模型转述（summary），也供前端可视化。"""
    raw = str(arguments.get("symbol", "")).strip()
    if not raw:
        return json.dumps(
            {"ok": False, "summary": "请提供期货品种（如 沪锡 / SN0 / rb2410）。"},
            ensure_ascii=False,
        )
    resolved = resolve_symbol(raw)
    try:
        n = int(arguments.get("bars", 120))
    except (TypeError, ValueError):
        n = 120
    n = max(30, min(n, 500))

    try:
        bars = _fetch_daily(resolved, n)
    except ImportError:
        return json.dumps(
            {"ok": False, "summary": "服务器未安装 akshare，请先 `pip install akshare`。"},
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {
                "ok": False,
                "symbol": raw,
                "resolved": resolved,
                "summary": f"拉取 {raw}（{resolved}）行情失败：{exc}。请确认品种/代码正确、服务器能访问新浪财经。",
            },
            ensure_ascii=False,
        )

    bars, notes = clean_bars(bars)
    if len(bars) < 30:
        return json.dumps(
            {
                "ok": False,
                "symbol": raw,
                "resolved": resolved,
                "summary": f"{raw}（{resolved}）有效数据不足（{len(bars)} 根），无法可靠判别。",
            },
            ensure_ascii=False,
        )

    analysis = analyze_123_2b(bars, window=3)
    return json.dumps(_build_result(raw, resolved, bars, analysis, notes), ensure_ascii=False)
