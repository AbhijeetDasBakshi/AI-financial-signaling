"""
Backtesting Report — Layer 5b
Assembles final API response from engine output + metrics.
Also builds the signal audit trail used for ML retraining.

The signal_log is the most valuable output for improving the 45% ML accuracy:
  - Shows exactly which signals were correct historically
  - Identifies which rule combinations actually work
  - Provides a retraining dataset with correct labels
"""
from backtesting.engine import run_backtest
from backtesting.metrics import compute_metrics


def generate_report(
    ticker:      str,
    period:      str   = "6mo",
    include_log: bool  = True,
    sentiment:   float = 0.0,
) -> dict:
    """
    Full backtesting report. Entry point called by the API route
    and the orchestrator.

    Args:
        ticker:      Stock symbol
        period:      Lookback period: 1mo, 3mo, 6mo, 1y, 2y
        include_log: Whether to include full signal_log in response
                     (can be large — ~1 entry per trading day)
        sentiment:   Sentiment score to use (historical sentiment unavailable)

    Returns:
        Complete report dict matching the documented API response shape
    """
    print(f"\n[BacktestReport] Generating report for {ticker} | {period}")

    # ── Run engine ─────────────────────────────────────────────────────
    raw = run_backtest(ticker, period=period, sentiment=sentiment)

    if raw.get("error"):
        return {
            "ticker":  ticker,
            "period":  period,
            "error":   raw["error"],
            "status":  "failed",
        }

    # ── Compute metrics ────────────────────────────────────────────────
    metrics = compute_metrics(raw)

    # ── Build summary ──────────────────────────────────────────────────
    report = {
        # Identity
        "ticker":  ticker,
        "period":  period,
        "status":  "success",

        # Core performance metrics (top-level for easy consumption)
        "win_rate":          metrics["win_rate"],
        "total_return":      metrics["total_return"],
        "sharpe_ratio":      metrics["sharpe_ratio"],
        "max_drawdown":      metrics["max_drawdown"],
        "signals_tested":    metrics["signals_tested"],

        # Trade counts
        "total_trades":      metrics["total_trades"],
        "profitable_trades": metrics["profitable_trades"],
        "hold_count":        metrics.get("hold_count", 0),
        "avg_hold_days":     metrics["avg_hold_days"],

        # Signal quality breakdown
        "accuracy_by_signal":    metrics["accuracy_by_signal"],
        "agreement_breakdown":   metrics["agreement_breakdown"],
        "conf_accuracy_buckets": metrics.get("conf_accuracy_buckets", {}),

        # Rule diagnostics — helps tune rule weights
        "best_rule":   metrics["best_rule"],
        "worst_rule":  metrics["worst_rule"],

        # ML diagnostics — directly addresses the 45% accuracy issue
        "ml_accuracy_avg":   metrics["ml_accuracy_avg"],
        "ml_accuracy_delta": metrics["ml_accuracy_delta"],
        "ml_accuracy_note":  _ml_note(metrics),
    }

    # ── Optional signal audit trail ────────────────────────────────────
    if include_log:
        report["signal_log"] = raw.get("signal_log", [])

    return report


def _ml_note(metrics: dict) -> str:
    """Human-readable note about ML performance for the dashboard."""
    avg   = metrics.get("ml_accuracy_avg")
    delta = metrics.get("ml_accuracy_delta")

    if avg is None:
        return "Insufficient ML data"

    note = f"Average ML accuracy across backtest windows: {avg * 100:.1f}%."

    if delta is not None:
        if delta > 0.02:
            note += f" Model improved by {delta * 100:.1f}pp over the period — retraining on recent data recommended."
        elif delta < -0.02:
            note += f" Model degraded by {abs(delta) * 100:.1f}pp — feature drift detected, consider retraining."
        else:
            note += " Model accuracy stable across the period."

    win_rate_raw = metrics.get("win_rate_raw", 0)
    if avg and avg < 0.50:
        note += " ML accuracy below 50% — rule engine signals are more reliable for this ticker."
    elif win_rate_raw and win_rate_raw > 0.55 and avg and avg >= 0.55:
        note += " Both rule and ML signals performing above baseline — consider increasing ML weight in confidence engine."

    return note
