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

# 参数（可调）：
ATR_PERIOD = 14
DEFAULT_ATR_MULT = 2.0   # ZigZag 反转阈值 = atr_mult × ATR，自适应品种波动
CONFIRM_ATR = 0.5        # 突破确认缓冲 = CONFIRM_ATR × ATR，过滤毛刺
TWOB_WINDOW = 5          # 2B 假突破的时间窗口（最近 N 根）
VOL_LOOKBACK = 20        # 量能均值回看


def _atr(bars: list[Bar], period: int = ATR_PERIOD) -> float:
    """近 period 根的平均真实波幅（简单均值）。"""
    trs = []
    for i in range(1, len(bars)):
        h, low, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - low, abs(h - pc), abs(low - pc)))
    if not trs:
        return 0.0
    period = min(period, len(trs))
    return sum(trs[-period:]) / period


def _zigzag(bars: list[Bar], rev: float) -> list[tuple[int, float, str]]:
    """ATR 自适应 ZigZag：价格自极值反向超过 rev 才确认一个摆动点。

    返回按时间排序的 (index, price, kind) 列表，kind ∈ {"H","L"}，交替出现。
    """
    n = len(bars)
    if n < 2 or rev <= 0:
        return []
    pivots: list[tuple[int, float, str]] = []
    trend = None  # None 未定；"up" 上升腿（找高点）；"down" 下降腿（找低点）
    up_i, up = 0, bars[0]["high"]
    dn_i, dn = 0, bars[0]["low"]
    for i in range(n):
        h, low = bars[i]["high"], bars[i]["low"]
        if trend in (None, "up"):
            if h >= up:
                up, up_i = h, i
            elif up - low >= rev:
                pivots.append((up_i, up, "H"))
                trend = "down"
                dn, dn_i = low, i
                continue
        if trend in (None, "down"):
            if low <= dn:
                dn, dn_i = low, i
            elif h - dn >= rev:
                pivots.append((dn_i, dn, "L"))
                trend = "up"
                up, up_i = h, i
    return pivots


def _trendline(p1: tuple[int, float], p2: tuple[int, float], x: int) -> float:
    """过两个摆动点的直线在 x 处的取值。"""
    (i1, v1), (i2, v2) = p1, p2
    if i2 == i1:
        return v2
    return v2 + (v2 - v1) / (i2 - i1) * (x - i2)


def _first_close_below(bars: list[Bar], level: float, start: int) -> int | None:
    for i in range(max(1, start), len(bars)):
        if bars[i]["close"] < level:
            return i
    return None


def _first_close_above(bars: list[Bar], level: float, start: int) -> int | None:
    for i in range(max(1, start), len(bars)):
        if bars[i]["close"] > level:
            return i
    return None


def _first_break_line(bars: list[Bar], p1, p2, confirm: float, start: int, below: bool):
    for i in range(max(1, start), len(bars)):
        line = _trendline(p1, p2, i)
        if (below and bars[i]["close"] < line - confirm) or (
            not below and bars[i]["close"] > line + confirm
        ):
            return i
    return None


def _vol_confirm(bars: list[Bar]) -> bool:
    vols = [float(b.get("volume", 0) or 0) for b in bars]
    if not any(vols):
        return False
    recent = sum(vols[-TWOB_WINDOW:]) / min(TWOB_WINDOW, len(vols))
    base = sum(vols[-VOL_LOOKBACK:]) / min(VOL_LOOKBACK, len(vols))
    return base > 0 and recent > base * 1.2


def _confidence(n_cond: int, ordered: bool, two_b: bool, vol: bool) -> int:
    score = n_cond * 18 + (15 if ordered else 0) + (25 if two_b else 0) + (8 if vol else 0)
    return max(0, min(100, score))


def _eval_bearish(bars, highs, lows, last, x, confirm, vol):
    prev_high = highs[-2][1]
    last_high_i, last_high = highs[-1]
    last_low_i, last_low = lows[-1]

    c1 = last < _trendline(lows[-2], lows[-1], x) - confirm       # ① 破上升趋势线
    c2 = last_high <= prev_high                                    # ② 反弹未创新高
    c3 = last < last_low - confirm                                 # ③ 跌破前期回调低点

    # 时序：先（在最后一个高点后）跌破趋势线，再跌破前低
    i1 = _first_break_line(bars, lows[-2], lows[-1], confirm, last_high_i, below=True)
    i3 = _first_close_below(bars, last_low - confirm, last_low_i + 1)
    ordered = c2 and i1 is not None and i3 is not None and i1 <= i3

    # 2B 顶：最近窗口内创出高于前高的新高，但收盘又回落到前高之下
    recent_high = max(b["high"] for b in bars[-TWOB_WINDOW:])
    two_b = recent_high > prev_high and last < prev_high - confirm

    conds = []
    if c1:
        conds.append("① 跌破上升趋势线")
    if c2:
        conds.append("② 反弹未创新高")
    if c3:
        conds.append("③ 跌破前期回调低点")
    return {
        "conditions": conds, "count": len(conds), "twoB": two_b,
        "c1": c1, "c2": c2, "c3": c3, "ordered": ordered,
        "confidence": _confidence(len(conds), ordered, two_b, vol),
    }


def _eval_bullish(bars, highs, lows, last, x, confirm, vol):
    prev_low = lows[-2][1]
    last_low_i, last_low = lows[-1]
    last_high_i, last_high = highs[-1]

    c1 = last > _trendline(highs[-2], highs[-1], x) + confirm      # ① 破下降趋势线
    c2 = last_low >= prev_low                                      # ② 回落未创新低
    c3 = last > last_high + confirm                                # ③ 突破前期反弹高点

    i1 = _first_break_line(bars, highs[-2], highs[-1], confirm, last_low_i, below=False)
    i3 = _first_close_above(bars, last_high + confirm, last_high_i + 1)
    ordered = c2 and i1 is not None and i3 is not None and i1 <= i3

    recent_low = min(b["low"] for b in bars[-TWOB_WINDOW:])
    two_b = recent_low < prev_low and last > prev_low + confirm

    conds = []
    if c1:
        conds.append("① 突破下降趋势线")
    if c2:
        conds.append("② 回落未创新低")
    if c3:
        conds.append("③ 突破前期反弹高点")
    return {
        "conditions": conds, "count": len(conds), "twoB": two_b,
        "c1": c1, "c2": c2, "c3": c3, "ordered": ordered,
        "confidence": _confidence(len(conds), ordered, two_b, vol),
    }


def analyze_123_2b(bars: list[Bar], atr_mult: float = DEFAULT_ATR_MULT) -> dict:
    """对日 K 序列做 123 / 2B 判别（ATR 自适应 ZigZag + 时序 + 确认 + 置信度）。纯函数。"""
    n = len(bars)
    if n < ATR_PERIOD + 5:
        return {"ok": False, "reason": f"数据不足（{n} 根，需 ≥{ATR_PERIOD + 5}）"}

    atr = _atr(bars, ATR_PERIOD)
    if atr <= 0:
        return {"ok": False, "reason": "波动异常（ATR=0），无法判别"}

    pivots = _zigzag(bars, atr_mult * atr)
    highs = [(i, p) for (i, p, k) in pivots if k == "H"]
    lows = [(i, p) for (i, p, k) in pivots if k == "L"]
    if len(highs) < 2 or len(lows) < 2:
        return {"ok": False, "reason": "有效摆动点不足（波动太小或数据太短），无法可靠判别"}

    last = bars[-1]["close"]
    x = n - 1
    confirm = CONFIRM_ATR * atr
    vol = _vol_confirm(bars)

    hh, hl = highs[-1][1] > highs[-2][1], lows[-1][1] > lows[-2][1]
    lh, ll = highs[-1][1] < highs[-2][1], lows[-1][1] < lows[-2][1]
    trend = "up" if (hh and hl) else "down" if (lh and ll) else "range"

    bear = _eval_bearish(bars, highs, lows, last, x, confirm, vol)
    bull = _eval_bullish(bars, highs, lows, last, x, confirm, vol)

    return {
        "ok": True,
        "trend": trend,
        "last_close": last,
        "atr": round(atr, 2),
        "pivot_highs": highs[-2:],
        "pivot_lows": lows[-2:],
        "bearish": bear,
        "bullish": bull,
        "confidence": {"bearish": bear["confidence"], "bullish": bull["confidence"]},
    }


_TREND_CN = {"up": "上升", "down": "下降", "range": "盘整/震荡"}


def format_analysis(symbol: str, bars: list[Bar], a: dict) -> str:
    if not a["ok"]:
        return f"{symbol}：{a['reason']}"

    highs = [round(p, 2) for _, p in a["pivot_highs"]]
    lows = [round(p, 2) for _, p in a["pivot_lows"]]
    bear, bull = a["bearish"], a["bullish"]

    def suffix(side):
        s = "；时序成立" if side["ordered"] else ""
        return s

    lines = [
        f"品种 {symbol} —— 最近 {len(bars)} 根日K（截至 {bars[-1]['date']}），ATR≈{a.get('atr')}",
        f"当前趋势：{_TREND_CN[a['trend']]}，最新收盘 {a['last_close']}",
        f"最近摆动高点：{highs}；摆动低点：{lows}",
        f"看跌 123 满足 {bear['count']}/3：{'、'.join(bear['conditions']) or '无'}"
        + suffix(bear)
        + ("；⚠ 2B 顶部假突破" if bear["twoB"] else "")
        + f"（置信度 {bear['confidence']}）",
        f"看涨 123 满足 {bull['count']}/3：{'、'.join(bull['conditions']) or '无'}"
        + suffix(bull)
        + ("；⚠ 2B 底部假突破" if bull["twoB"] else "")
        + f"（置信度 {bull['confidence']}）",
    ]

    # 参考结论（agent 会据此展开叙述）—— 用置信度而非简单计数
    cb, cu = bear["confidence"], bull["confidence"]
    if cb >= 50 and cb >= cu:
        lines.append(f"参考结论：出现见顶信号（置信度 {cb}），警惕反转；空头止损参考最近摆动高点上方。")
    elif cu >= 50 and cu > cb:
        lines.append(f"参考结论：出现见底信号（置信度 {cu}），关注反转；多头止损参考最近摆动低点下方。")
    else:
        lines.append("参考结论：无高置信度的 123/2B 反转确认，趋势延续或盘整为主。")
    return "\n".join(lines)


# ----------------------------- 数据拉取 -----------------------------

_COLS = {
    "date": ["date", "日期", "时间"],
    "open": ["open", "开盘价", "开盘"],
    "high": ["high", "最高价", "最高"],
    "low": ["low", "最低价", "最低"],
    "close": ["close", "收盘价", "收盘"],
    "volume": ["volume", "成交量", "vol"],
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

    # 先按日期升序排，再取最近 n 根 —— 防止数据源为降序时 tail() 取到最老数据
    if mapping["date"] is not None:
        df = df.sort_values(by=mapping["date"])
    tail = df.tail(n)
    bars: list[Bar] = []
    for _, row in tail.iterrows():
        bar = {
            "date": str(row[mapping["date"]]) if mapping["date"] else "",
            "open": float(row[mapping["open"]]),
            "high": float(row[mapping["high"]]),
            "low": float(row[mapping["low"]]),
            "close": float(row[mapping["close"]]),
        }
        if mapping["volume"] is not None:
            try:
                bar["volume"] = float(row[mapping["volume"]])
            except (TypeError, ValueError):
                bar["volume"] = 0.0
        bars.append(bar)
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
        "atr": analysis.get("atr"),
        "confidence": analysis.get("confidence"),
        "pivots": {"highs": highs, "lows": lows},
        "bearish": {
            "count": bear["count"],
            "twoB": bear["twoB"],
            "ordered": bear.get("ordered", False),
            "confidence": bear.get("confidence", 0),
            "conditions": _conditions(bear, _BEAR_LABEL),
        },
        "bullish": {
            "count": bull["count"],
            "twoB": bull["twoB"],
            "ordered": bull.get("ordered", False),
            "confidence": bull.get("confidence", 0),
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

    analysis = analyze_123_2b(bars)
    return json.dumps(_build_result(raw, resolved, bars, analysis, notes), ensure_ascii=False)
