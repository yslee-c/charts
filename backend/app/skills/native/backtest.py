"""123 / 2B 策略回测（walk-forward，无未来函数）。

逐日：只用「截至当日」的数据跑 analyze，产生信号；在**次日**开/平仓，
避免用到未来信息。信号取置信度 ≥ 阈值且方向占优的一侧。

平仓条件：触及止损（进场时的对侧摆动点）/ 出现反向信号 / 达到最大持仓天数。
指标：交易数、胜率、盈亏比、总/平均收益、平均盈亏、最大回撤、资金曲线。

纯函数，可脱离网络单测。
"""
from app.skills.native.futures_trend import Bar, analyze_123_2b

WARMUP = 40          # 前 WARMUP 根用于形成摆动结构，不交易
DEFAULT_ENTRY_CONF = 50
DEFAULT_MAX_HOLD = 20


def _signal(analysis: dict, entry_conf: int) -> tuple[str | None, float | None]:
    """由分析结果得出方向与止损位。"""
    if not analysis.get("ok"):
        return None, None
    bear, bull = analysis["bearish"], analysis["bullish"]
    ph = analysis["pivot_highs"][-1][1]
    pl = analysis["pivot_lows"][-1][1]
    if bear["confidence"] >= entry_conf and bear["confidence"] >= bull["confidence"]:
        return "short", ph  # 止损：最近摆动高点上方
    if bull["confidence"] >= entry_conf and bull["confidence"] > bear["confidence"]:
        return "long", pl   # 止损：最近摆动低点下方
    return None, None


def _close(pos: dict, exit_price: float, exit_date: str, reason: str) -> dict:
    entry = pos["entry_price"]
    ret = (
        (exit_price - entry) / entry
        if pos["side"] == "long"
        else (entry - exit_price) / entry
    )
    return {
        "side": pos["side"],
        "entry_date": pos["entry_date"],
        "exit_date": exit_date,
        "entry": round(entry, 2),
        "exit": round(exit_price, 2),
        "reason": reason,
        "return_pct": round(ret * 100, 2),
    }


def _metrics(trades: list[dict], equity: list[float]) -> dict:
    n = len(trades)
    if n == 0:
        return {
            "trades": 0, "win_rate": 0.0, "total_return": 0.0, "avg_return": 0.0,
            "profit_factor": None, "avg_win": 0.0, "avg_loss": 0.0, "max_drawdown": 0.0,
        }
    rets = [t["return_pct"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    peak = equity[0]
    max_dd = 0.0
    for e in equity:
        peak = max(peak, e)
        max_dd = max(max_dd, peak - e)

    return {
        "trades": n,
        "win_rate": round(len(wins) / n * 100, 1),
        "total_return": round(sum(rets), 2),
        "avg_return": round(sum(rets) / n, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "avg_win": round(gross_win / len(wins), 2) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "max_drawdown": round(max_dd, 2),
    }


def backtest_123_2b(
    bars: list[Bar],
    entry_conf: int = DEFAULT_ENTRY_CONF,
    max_hold: int = DEFAULT_MAX_HOLD,
    warmup: int = WARMUP,
) -> dict:
    n = len(bars)
    if n < warmup + 10:
        return {"ok": False, "reason": f"数据不足以回测（{n} 根，需 ≥{warmup + 10}）"}

    trades: list[dict] = []
    equity_curve: list[float] = []
    cum = 0.0
    pos: dict | None = None

    for i in range(warmup, n - 1):
        nxt = bars[i + 1]
        sig, stop = _signal(analyze_123_2b(bars[: i + 1]), entry_conf)

        # 先管理已有持仓
        if pos is not None:
            exit_price = None
            reason = None
            if pos["side"] == "long" and nxt["low"] <= pos["stop"]:
                exit_price, reason = pos["stop"], "止损"
            elif pos["side"] == "short" and nxt["high"] >= pos["stop"]:
                exit_price, reason = pos["stop"], "止损"
            if exit_price is None and sig and sig != pos["side"]:
                exit_price, reason = nxt["open"], "反向信号"
            if exit_price is None and (i + 1 - pos["entry_i"]) >= max_hold:
                exit_price, reason = nxt["open"], "到期"
            if exit_price is not None:
                trade = _close(pos, exit_price, nxt["date"], reason)
                trades.append(trade)
                cum += trade["return_pct"]
                equity_curve.append(round(cum, 2))
                pos = None

        # 空仓且有信号 → 次日开盘进场
        if pos is None and sig:
            pos = {
                "side": sig,
                "entry_price": nxt["open"],
                "entry_i": i + 1,
                "stop": stop,
                "entry_date": nxt["date"],
            }

    # 收盘平掉未了结持仓
    if pos is not None:
        trade = _close(pos, bars[-1]["close"], bars[-1]["date"], "回测结束")
        trades.append(trade)
        cum += trade["return_pct"]
        equity_curve.append(round(cum, 2))

    return {
        "ok": True,
        "params": {"entry_conf": entry_conf, "max_hold": max_hold, "warmup": warmup},
        "metrics": _metrics(trades, equity_curve or [0.0]),
        "equity": equity_curve,
        "trades": trades,
    }
