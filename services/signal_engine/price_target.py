"""
Price target engine.
Computes support and resistance levels from historical price data.
Uses pivot points, recent highs/lows, and MA levels.
"""
import pandas as pd
import numpy as np


def compute_price_targets(records: list[dict], current_price: float) -> dict:
    """
    Compute support/resistance levels and price targets.

    Support  = price floor (where price tends to bounce up)
    Resistance = price ceiling (where price tends to reverse down)
    """
    if not records or len(records) < 10:
        return {"error": "Not enough data for price targets"}

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)

    prices = df["price"].values
    highs  = df["high"].values  if "high"  in df.columns else prices
    lows   = df["low"].values   if "low"   in df.columns else prices

    # ── Pivot points (classic method) ────────────────────────
    last_high  = float(highs[-1])
    last_low   = float(lows[-1])
    last_close = float(prices[-1])

    pivot = (last_high + last_low + last_close) / 3
    r1    = (2 * pivot) - last_low
    r2    = pivot + (last_high - last_low)
    s1    = (2 * pivot) - last_high
    s2    = pivot - (last_high - last_low)

    # ── Recent highs/lows (20-day) ────────────────────────────
    recent    = df.tail(20)
    res_20d   = float(recent["high"].max()  if "high" in df.columns else recent["price"].max())
    sup_20d   = float(recent["low"].min()   if "low"  in df.columns else recent["price"].min())

    # ── MA levels as dynamic support/resistance ───────────────
    ma20 = float(df["price"].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
    ma50 = float(df["price"].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None

    # ── Price targets based on signal ────────────────────────
    upside_target   = round(min(r1, res_20d), 2)
    downside_target = round(max(s1, sup_20d), 2)

    # ── Distance from current price ──────────────────────────
    upside_pct   = round((upside_target   - current_price) / current_price * 100, 2)
    downside_pct = round((downside_target - current_price) / current_price * 100, 2)

    return {
        "current_price":    round(current_price, 2),
        "resistance": {
            "r1":           round(r1, 2),
            "r2":           round(r2, 2),
            "recent_high":  round(res_20d, 2),
        },
        "support": {
            "s1":           round(s1, 2),
            "s2":           round(s2, 2),
            "recent_low":   round(sup_20d, 2),
        },
        "ma_levels": {
            "ma20":         round(ma20, 2) if ma20 else None,
            "ma50":         round(ma50, 2) if ma50 else None,
        },
        "targets": {
            "upside":       upside_target,
            "upside_pct":   f"+{upside_pct}%",
            "downside":     downside_target,
            "downside_pct": f"{downside_pct}%",
        }
    }
