"""
Backtesting Metrics — Layer 5b
Pure math functions. Takes trade list from engine.py,
returns all performance statistics.

Metrics computed:
  - win_rate:          % of directional trades that were correct
  - total_return:      compound return across all BUY/SELL trades
  - sharpe_ratio:      annualised risk-adjusted return (daily returns, rf=0)
  - max_drawdown:      largest peak-to-trough loss in equity curve
  - signals_tested:    total windows evaluated
  - profitable_trades: count of positive P&L trades
  - total_trades:      BUY + SELL trades (HOLD excluded)
  - avg_hold_days:     always 1 (next-day exit strategy)
  - accuracy_by_signal: win rate split by BUY vs SELL
  - best_rule:         rule reason string most correlated with correct trades
  - worst_rule:        rule reason string most correlated with wrong trades
  - ml_accuracy_avg:   mean ML model accuracy across all windows
  - ml_accuracy_delta: difference between early and late windows (improvement indicator)
  - agreement_breakdown: STRONG/MODERATE/CONFLICTED counts
"""
import math
from collections import defaultdict


def compute_metrics(backtest_result: dict) -> dict:
    """
    Main entry point. Takes raw backtest output from engine.run_backtest()
    and returns full metrics dict ready for the API response.
    """
    trades     = backtest_result.get("trades", [])
    ticker     = backtest_result.get("ticker", "")
    period     = backtest_result.get("period", "")
    total_days = backtest_result.get("total_days", 0)

    if not trades:
        return _empty_metrics(ticker, period)

    # ── Split into actionable trades (BUY/SELL) and HOLD ──────────────
    actionable = [t for t in trades if t["signal"] in ("BUY", "SELL")]
    hold_count = len([t for t in trades if t["signal"] == "HOLD"])

    if not actionable:
        return _empty_metrics(ticker, period)

    # ── Win rate ───────────────────────────────────────────────────────
    scored    = [t for t in actionable if t["correct"] is not None]
    correct   = [t for t in scored if t["correct"]]
    win_rate  = len(correct) / len(scored) if scored else 0.0

    # ── Total return (compound) ────────────────────────────────────────
    compound = 1.0
    for t in actionable:
        compound *= (1.0 + t["pnl"])
    total_return = compound - 1.0

    # ── Daily P&L series for Sharpe + drawdown ─────────────────────────
    daily_pnls = [t["pnl"] for t in actionable]

    sharpe      = _sharpe_ratio(daily_pnls)
    max_dd      = _max_drawdown(daily_pnls)

    # ── Profitable trades ──────────────────────────────────────────────
    profitable = [t for t in actionable if t["pnl"] > 0]

    # ── Accuracy by signal direction ───────────────────────────────────
    accuracy_by_signal = _accuracy_by_signal(actionable)

    # ── Rule analysis ─────────────────────────────────────────────────
    best_rule, worst_rule = _rule_analysis(actionable)

    # ── ML accuracy trend ─────────────────────────────────────────────
    ml_accuracies = [t["ml_accuracy"] for t in trades if t.get("ml_accuracy") is not None]
    ml_accuracy_avg   = round(sum(ml_accuracies) / len(ml_accuracies), 4) if ml_accuracies else None
    ml_accuracy_delta = _ml_accuracy_delta(ml_accuracies)

    # ── Agreement breakdown ────────────────────────────────────────────
    agreement_breakdown = defaultdict(int)
    for t in trades:
        agreement_breakdown[t.get("agreement", "UNKNOWN")] += 1

    # ── Confidence vs accuracy correlation ────────────────────────────
    conf_accuracy = _confidence_accuracy_buckets(scored)

    return {
        "ticker":         ticker,
        "period":         period,
        "total_days":     total_days,
        "signals_tested": len(trades),

        # Core metrics
        "win_rate":          f"{win_rate * 100:.1f}%",
        "win_rate_raw":      round(win_rate, 4),
        "total_return":      f"{total_return * 100:+.2f}%",
        "total_return_raw":  round(total_return, 6),
        "sharpe_ratio":      sharpe,
        "max_drawdown":      f"{max_dd * 100:.2f}%",
        "max_drawdown_raw":  round(max_dd, 6),

        # Trade counts
        "total_trades":      len(actionable),
        "profitable_trades": len(profitable),
        "hold_count":        hold_count,
        "avg_hold_days":     1,            # fixed: next-day exit strategy

        # Signal breakdown
        "accuracy_by_signal":   accuracy_by_signal,
        "agreement_breakdown":  dict(agreement_breakdown),
        "conf_accuracy_buckets": conf_accuracy,

        # Rule diagnostics
        "best_rule":  best_rule,
        "worst_rule": worst_rule,

        # ML diagnostics
        "ml_accuracy_avg":   ml_accuracy_avg,
        "ml_accuracy_delta": ml_accuracy_delta,
    }


# ── Private helpers ────────────────────────────────────────────────────────


def _sharpe_ratio(daily_pnls: list[float], risk_free: float = 0.0) -> float:
    """
    Annualised Sharpe ratio from daily P&L list.
    Sharpe = (mean_return - rf) / std_return * sqrt(252)
    Returns 0.0 if insufficient data or zero variance.
    """
    if len(daily_pnls) < 2:
        return 0.0

    n    = len(daily_pnls)
    mean = sum(daily_pnls) / n
    variance = sum((x - mean) ** 2 for x in daily_pnls) / (n - 1)
    std  = math.sqrt(variance) if variance > 0 else 0.0

    if std == 0.0:
        return 0.0

    daily_sharpe = (mean - risk_free) / std
    return round(daily_sharpe * math.sqrt(252), 4)


def _max_drawdown(daily_pnls: list[float]) -> float:
    """
    Maximum peak-to-trough drawdown from P&L series.
    Returns a negative float (e.g. -0.084 = -8.4% drawdown).
    """
    if not daily_pnls:
        return 0.0

    equity   = 1.0
    peak     = 1.0
    max_dd   = 0.0

    for pnl in daily_pnls:
        equity *= (1.0 + pnl)
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak
        if dd < max_dd:
            max_dd = dd

    return round(max_dd, 6)


def _accuracy_by_signal(actionable: list[dict]) -> dict:
    """Win rate split by BUY vs SELL signals."""
    result = {}
    for direction in ("BUY", "SELL"):
        subset  = [t for t in actionable if t["signal"] == direction and t["correct"] is not None]
        correct = [t for t in subset if t["correct"]]
        result[direction] = {
            "count":    len(subset),
            "correct":  len(correct),
            "win_rate": f"{(len(correct) / len(subset) * 100):.1f}%" if subset else "N/A",
        }
    return result


def _rule_analysis(actionable: list[dict]) -> tuple[str | None, str | None]:
    """
    Identify which rule reason strings most correlate with correct vs wrong trades.
    Returns (best_rule, worst_rule) as plain strings.
    """
    reason_correct = defaultdict(int)
    reason_total   = defaultdict(int)

    for trade in actionable:
        if trade["correct"] is None:
            continue
        for reason in trade.get("reasons", []):
            # Normalise: strip the numeric part to group similar reasons
            key = reason.split("—")[0].strip() if "—" in reason else reason[:60]
            reason_total[key]  += 1
            if trade["correct"]:
                reason_correct[key] += 1

    if not reason_total:
        return None, None

    # Only consider reasons that appeared at least 5 times
    qualified = {k: v for k, v in reason_total.items() if v >= 5}
    if not qualified:
        return None, None

    rates = {k: reason_correct[k] / v for k, v in qualified.items()}

    best  = max(rates, key=rates.get)
    worst = min(rates, key=rates.get)

    best_str  = f"{best} ({rates[best]*100:.1f}% win rate, n={reason_total[best]})"
    worst_str = f"{worst} ({rates[worst]*100:.1f}% win rate, n={reason_total[worst]})"

    return best_str, worst_str


def _ml_accuracy_delta(ml_accuracies: list[float]) -> float | None:
    """
    Compare average ML accuracy in the first half vs second half of the backtest.
    Positive delta = model improved over time (good sign for retraining).
    """
    if not ml_accuracies or len(ml_accuracies) < 10:
        return None

    mid   = len(ml_accuracies) // 2
    early = sum(ml_accuracies[:mid]) / mid
    late  = sum(ml_accuracies[mid:]) / (len(ml_accuracies) - mid)
    return round(late - early, 4)


def _confidence_accuracy_buckets(scored: list[dict]) -> dict:
    """
    Break accuracy down by confidence bucket: low (<0.6), medium (0.6-0.75), high (>0.75).
    Tells you if high-confidence signals are actually more accurate.
    """
    buckets = {
        "low":    {"range": "<0.60",   "trades": [], "correct": 0},
        "medium": {"range": "0.60-0.75", "trades": [], "correct": 0},
        "high":   {"range": ">0.75",   "trades": [], "correct": 0},
    }

    for t in scored:
        conf = t.get("confidence", 0)
        if conf < 0.60:
            key = "low"
        elif conf < 0.75:
            key = "medium"
        else:
            key = "high"
        buckets[key]["trades"].append(t)
        if t["correct"]:
            buckets[key]["correct"] += 1

    result = {}
    for key, data in buckets.items():
        n = len(data["trades"])
        result[key] = {
            "range":    data["range"],
            "count":    n,
            "win_rate": f"{(data['correct'] / n * 100):.1f}%" if n else "N/A",
        }
    return result


def _empty_metrics(ticker: str, period: str) -> dict:
    return {
        "ticker":         ticker,
        "period":         period,
        "signals_tested": 0,
        "win_rate":       "N/A",
        "total_return":   "N/A",
        "sharpe_ratio":   None,
        "max_drawdown":   "N/A",
        "total_trades":   0,
        "profitable_trades": 0,
        "note":           "Insufficient data for backtesting",
    }
