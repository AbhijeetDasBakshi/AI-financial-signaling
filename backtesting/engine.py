"""
Backtesting Engine — Layer 5b
Replays rule + ML signals over historical price windows.
No lookahead: each window only uses data available up to that point.

Strategy:
  - For each day D (starting at window_size), slice records[0:D]
  - Generate rule signal + ML signal → combined signal
  - Entry at close price on day D
  - Exit at close price on day D+1 (next-day exit)
  - Score: was the direction correct? What was the P&L?

Usage:
  from backtesting.engine import run_backtest
  result = run_backtest("NVDA", period="6mo")
"""
import time
from services.data_ingestion.price_service import PriceService
from services.signal_engine.rule_engine import _compute_features, get_average_sentiment
from services.signal_engine.ml_engine import train_and_predict
from services.signal_engine.confidence_engine import compute_combined_signal

# Minimum window of records needed to compute RSI(14) + MA(20) cleanly
MIN_WINDOW = 30


def _compute_rule_signal_from_records(records: list[dict], sentiment: float = 0.0) -> dict:
    """
    Compute rule signal from a slice of records.
    Mirrors rule_engine.compute_signal() but accepts records directly
    so we don't trigger the live Yahoo Finance fetch.
    """
    features = _compute_features(records)
    score    = 0.0
    reasons  = []

    if features:
        ma5  = features.get("ma5")
        ma10 = features.get("ma10")
        ma20 = features.get("ma20")
        pct  = features.get("pct_change")
        rsi  = features.get("rsi")
        vol  = features.get("vol_vs_avg")

        if ma5 and ma10:
            if ma5 > ma10:
                score += 1.0
                reasons.append(f"MA5 above MA10 — bullish crossover")
            else:
                score -= 1.0
                reasons.append(f"MA5 below MA10 — bearish crossover")

        if ma5 and ma20:
            if ma5 > ma20:
                score += 0.5
                reasons.append(f"MA5 above MA20 — medium-term bullish")
            else:
                score -= 0.5
                reasons.append(f"MA5 below MA20 — medium-term bearish")

        if rsi is not None:
            if rsi < 30:
                score += 1.0
                reasons.append(f"RSI {rsi:.1f} — oversold")
            elif rsi > 70:
                score -= 1.0
                reasons.append(f"RSI {rsi:.1f} — overbought")

        if pct is not None:
            if pct > 0.01:
                score += 0.5
            elif pct < -0.01:
                score -= 0.5

        if vol is not None:
            if vol > 1.5:
                score += 0.5

    if sentiment > 0.2:
        score += 1.0
    elif sentiment < -0.2:
        score -= 1.0

    if score >= 2.0:
        signal     = "BUY"
        confidence = min(0.55 + (score * 0.08), 0.95)
    elif score <= -2.0:
        signal     = "SELL"
        confidence = min(0.55 + (abs(score) * 0.08), 0.95)
    else:
        signal     = "HOLD"
        confidence = round(0.5 + (abs(score) * 0.02), 2)

    return {
        "signal":     signal,
        "confidence": round(confidence, 2),
        "score":      round(score, 2),
        "reasons":    reasons,
    }


def run_backtest(
    ticker:      str,
    period:      str  = "6mo",
    window_size: int  = MIN_WINDOW,
    sentiment:   float = 0.0,
) -> dict:
    """
    Full backtest over historical price data.

    Args:
        ticker:      Stock symbol e.g. "NVDA"
        period:      Yahoo Finance period string: 1mo, 3mo, 6mo, 1y, 2y
        window_size: Minimum days of history needed before generating a signal
        sentiment:   Fixed sentiment score to use (live sentiment not available historically)

    Returns:
        dict with trades list + summary metrics (pre-metrics.py aggregation)
    """
    ticker = ticker.upper()
    print(f"\n[Backtest] Starting backtest for {ticker} | period={period} | window={window_size}")

    price_svc = PriceService()
    records   = price_svc.get_historical_prices(ticker, period=period)

    if not records:
        return {
            "ticker":  ticker,
            "error":   "No historical data available",
            "trades":  [],
            "period":  period,
        }

    # Sort ascending by timestamp — oldest first
    records = sorted(records, key=lambda r: r["timestamp"])
    total   = len(records)

    if total < window_size + 1:
        return {
            "ticker":  ticker,
            "error":   f"Insufficient data: {total} records, need {window_size + 1}",
            "trades":  [],
            "period":  period,
        }

    print(f"[Backtest] {total} records loaded. Running {total - window_size} windows...")

    trades     = []
    signal_log = []

    for i in range(window_size, total - 1):
        window     = records[:i]          # only past data — no lookahead
        entry_rec  = records[i]           # signal generated at close of day i
        exit_rec   = records[i + 1]       # trade resolved at close of day i+1

        entry_price = entry_rec.get("price") or entry_rec.get("close")
        exit_price  = exit_rec.get("price")  or exit_rec.get("close")

        if not entry_price or not exit_price:
            continue

        # ── Rule signal (no Yahoo call — uses window slice directly) ──
        rule_result = _compute_rule_signal_from_records(window, sentiment)

        # ── ML signal (trained only on window — no future data) ──
        ml_result = train_and_predict(window)

        rule_clean = {
            "signal":     rule_result["signal"],
            "confidence": rule_result["confidence"],
        }
        ml_clean = {
            "signal":     ml_result.get("ml_signal", "INSUFFICIENT_DATA"),
            "confidence": ml_result.get("ml_confidence", 0.5),
            "accuracy":   ml_result.get("ml_accuracy"),
        }

        combined = compute_combined_signal(rule_clean, ml_clean)
        signal   = combined["signal"]

        # ── Score the trade ────────────────────────────────────────────
        actual_direction = "UP" if exit_price > entry_price else "DOWN"
        pct_change       = (exit_price - entry_price) / entry_price

        if signal == "BUY":
            pnl     = pct_change
            correct = actual_direction == "UP"
        elif signal == "SELL":
            pnl     = -pct_change          # short position profits from decline
            correct = actual_direction == "DOWN"
        else:
            pnl     = 0.0
            correct = None                 # HOLD — not scored

        trade = {
            "date":             str(entry_rec.get("timestamp", ""))[:10],
            "signal":           signal,
            "confidence":       combined["confidence"],
            "agreement":        combined["agreement"],
            "rule_signal":      combined["rule_signal"],
            "ml_signal":        combined["ml_signal"],
            "entry_price":      round(entry_price, 4),
            "exit_price":       round(exit_price, 4),
            "pct_change":       round(pct_change, 6),
            "pnl":              round(pnl, 6),
            "correct":          correct,
            "actual_direction": actual_direction,
            "ml_accuracy":      ml_result.get("ml_accuracy"),
            "reasons":          rule_result.get("reasons", []),
        }

        trades.append(trade)
        signal_log.append({
            "date":       trade["date"],
            "signal":     signal,
            "correct":    correct,
            "pnl":        trade["pnl"],
            "agreement":  combined["agreement"],
        })

        if i % 20 == 0:
            print(f"[Backtest] Progress: {i - window_size + 1}/{total - window_size} windows")

    print(f"[Backtest] Complete. {len(trades)} trades generated.")

    return {
        "ticker":     ticker,
        "period":     period,
        "trades":     trades,
        "signal_log": signal_log,
        "total_days": total,
    }
