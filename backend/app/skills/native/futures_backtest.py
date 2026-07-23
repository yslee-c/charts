"""内置 native skill：123 / 2B 策略历史回测。

复用 futures_trend 的数据拉取与清洗，跑 backtest_123_2b，返回结构化指标。
"""
import json

from app.skills.native.backtest import backtest_123_2b
from app.skills.native.futures_trend import clean_bars
from app.skills.native.symbols import resolve_symbol


def _summary(label: str, m: dict, n_bars: int) -> str:
    pf = m["profit_factor"]
    pf_s = f"{pf}" if pf is not None else "—（无亏损交易）"
    return (
        f"{label} —— 123/2B 策略回测（{n_bars} 根日K）：\n"
        f"共 {m['trades']} 笔交易，胜率 {m['win_rate']}%，盈亏比 {pf_s}，"
        f"累计收益 {m['total_return']}%，单笔均收益 {m['avg_return']}%，"
        f"最大回撤 {m['max_drawdown']}%。\n"
        f"注：按次日开盘进出、以摆动点为止损的简化模型，含滑点/手续费前，仅供参考、非投资建议。"
    )


def run(arguments: dict) -> str:
    raw = str(arguments.get("symbol", "")).strip()
    if not raw:
        return json.dumps(
            {"ok": False, "summary": "请提供期货品种（如 沪锡 / SN0）。"},
            ensure_ascii=False,
        )
    resolved = resolve_symbol(raw)

    def _int(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(arguments.get(key, default))))
        except (TypeError, ValueError):
            return default

    n = _int("bars", 500, 100, 1500)
    entry_conf = _int("entry_conf", 50, 0, 100)
    max_hold = _int("max_hold", 20, 2, 120)

    # 惰性导入，复用 futures_trend 的拉取
    from app.skills.native.futures_trend import _fetch_daily

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
                "summary": f"拉取 {raw}（{resolved}）行情失败：{exc}。",
            },
            ensure_ascii=False,
        )

    bars, notes = clean_bars(bars)
    result = backtest_123_2b(bars, entry_conf=entry_conf, max_hold=max_hold)
    if not result["ok"]:
        return json.dumps(
            {"ok": False, "symbol": raw, "resolved": resolved, "summary": result["reason"]},
            ensure_ascii=False,
        )

    label = f"{raw}（{resolved}）"
    return json.dumps(
        {
            "ok": True,
            "kind": "backtest",
            "symbol": raw,
            "resolved": resolved,
            "bars_count": len(bars),
            "params": result["params"],
            "metrics": result["metrics"],
            "equity": result["equity"],
            "trades": result["trades"][-20:],  # 最近 20 笔
            "notes": notes,
            "summary": _summary(label, result["metrics"], len(bars)),
        },
        ensure_ascii=False,
    )
