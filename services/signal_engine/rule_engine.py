"""
Rule-based signal engine.
- Fetches 3mo history from Yahoo Finance with 1hr cooldown
- Caches in memory — no repeated Yahoo calls
- Falls back to prices_clean DB if Yahoo fails
"""
import time
import pandas as pd
from database.db import SessionLocal, news_collection
from database.models import PriceClean
from sqlalchemy import desc
from services.data_ingestion.price_service import PriceService

price_svc = PriceService()

# ── In-memory history cache ────────────────────────────────────
_history_cache: dict[str, tuple[float, list]] = {}
HISTORY_COOLDOWN = 3600   # 1 hour — change to 1800 for 30min etc.


def get_historical_features(ticker: str) -> dict | None:
    """
    Fetch 3mo price history with 1hr cooldown.
    First call → Yahoo Finance (3mo data)
    Next calls within 1hr → memory cache
    After 1hr → refresh from Yahoo
    Server restart → cache clears, fetches fresh
    """
    ticker = ticker.upper()
    now    = time.time()

    # ── Check cache ───────────────────────────────────────────
    if ticker in _history_cache:
        cached_time, cached_records = _history_cache[ticker]
        elapsed   = now - cached_time
        remaining = int(HISTORY_COOLDOWN - elapsed)

        if elapsed < HISTORY_COOLDOWN:
            print(f"[RuleEngine] Using cached history for {ticker} — refreshes in {remaining}s")
            return _compute_features(cached_records)

    # ── Fetch fresh from Yahoo Finance ────────────────────────
    print(f"[RuleEngine] Fetching fresh 3mo history for {ticker} from Yahoo Finance...")
    records = price_svc.get_historical_prices(ticker, period="3mo")

    if records:
        _history_cache[ticker] = (now, records)
        print(f"[RuleEngine] Cached {len(records)} records for {ticker}")
        return _compute_features(records)

    # ── Fallback — read from prices_clean DB ──────────────────
    print(f"[RuleEngine] Yahoo failed — falling back to prices_clean DB for {ticker}")
    return _features_from_db(ticker)


def _compute_features(records: list[dict]) -> dict | None:
    """Compute technical indicators from price records."""
    if not records:
        return None

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)

    # Moving averages
    df["ma5"]  = df["price"].rolling(5).mean()
    df["ma10"] = df["price"].rolling(10).mean()
    df["ma20"] = df["price"].rolling(20).mean()

    # % change
    df["pct_change"] = df["price"].pct_change()

    # RSI (14-period)
    delta      = df["price"].diff()
    gain       = delta.clip(lower=0).rolling(14).mean()
    loss       = (-delta.clip(upper=0)).rolling(14).mean()
    rs         = gain / loss.replace(0, float("nan"))
    df["rsi"]  = 100 - (100 / (1 + rs))

    # Volume trend
    df["vol_ma10"]   = df["volume"].rolling(10).mean()
    df["vol_vs_avg"] = df["volume"] / df["vol_ma10"]

    latest = df.iloc[-1]

    def safe(val):
        return round(float(val), 4) if pd.notna(val) else None

    return {
        "price":       safe(latest["price"]),
        "ma5":         safe(latest["ma5"]),
        "ma10":        safe(latest["ma10"]),
        "ma20":        safe(latest["ma20"]),
        "pct_change":  safe(latest["pct_change"]),
        "rsi":         round(float(latest["rsi"]), 2) if pd.notna(latest["rsi"]) else None,
        "volume":      int(latest["volume"]),
        "vol_vs_avg":  safe(latest["vol_vs_avg"]),
        "high_52w":    round(float(df["price"].max()), 4),
        "low_52w":     round(float(df["price"].min()), 4),
        "data_points": len(df),
    }


def _features_from_db(ticker: str) -> dict | None:
    """Fallback — read latest features from prices_clean table."""
    db = SessionLocal()
    try:
        records = (
            db.query(PriceClean)
            .filter(PriceClean.ticker == ticker.upper())
            .order_by(desc(PriceClean.timestamp))
            .limit(60)
            .all()
        )
        if not records:
            print(f"[RuleEngine] No data found for {ticker} in DB either.")
            return None

        data = [{
            "price":     r.price,
            "open":      r.open,
            "high":      r.high,
            "low":       r.low,
            "volume":    r.volume,
            "timestamp": r.timestamp,
        } for r in reversed(records)]

        return _compute_features(data)
    finally:
        db.close()


def get_average_sentiment(ticker: str, limit: int = 10) -> float:
    """Get average sentiment from MongoDB."""
    try:
        cursor = (
            news_collection
            .find(
                {"ticker": ticker.upper(), "sentiment": {"$ne": 0, "$exists": True}},
                {"_id": 0, "sentiment": 1}
            )
            .sort("ingested_at", -1)
            .limit(limit)
        )
        scores = [doc["sentiment"] for doc in cursor if isinstance(doc.get("sentiment"), float)]
        return round(sum(scores) / len(scores), 4) if scores else 0.0
    except Exception as e:
        print(f"[RuleEngine] Sentiment error: {e}")
        return 0.0


def compute_signal(ticker: str, live_sentiment: float = None) -> dict:
    """
    Compute BUY/SELL/HOLD signal using:
    - MA crossover (MA5 vs MA10, MA5 vs MA20)
    - RSI overbought/oversold
    - Price momentum
    - Volume conviction
    - News sentiment
    """
    ticker    = ticker.upper()
    features  = get_historical_features(ticker)
    sentiment = live_sentiment if live_sentiment is not None else get_average_sentiment(ticker)

    score   = 0.0
    reasons = []

    if features:
        ma5  = features.get("ma5")
        ma10 = features.get("ma10")
        ma20 = features.get("ma20")
        pct  = features.get("pct_change")
        rsi  = features.get("rsi")
        vol  = features.get("vol_vs_avg")

        # MA crossover
        if ma5 and ma10:
            if ma5 > ma10:
                score += 1.0
                reasons.append(f"MA5 ({ma5:.2f}) above MA10 ({ma10:.2f}) — bullish crossover")
            else:
                score -= 1.0
                reasons.append(f"MA5 ({ma5:.2f}) below MA10 ({ma10:.2f}) — bearish crossover")

        if ma5 and ma20:
            if ma5 > ma20:
                score += 0.5
                reasons.append(f"MA5 above MA20 ({ma20:.2f}) — medium-term bullish")
            else:
                score -= 0.5
                reasons.append(f"MA5 below MA20 ({ma20:.2f}) — medium-term bearish")

        # RSI
        if rsi is not None:
            if rsi < 30:
                score += 1.0
                reasons.append(f"RSI {rsi:.1f} — oversold, potential reversal")
            elif rsi > 70:
                score -= 1.0
                reasons.append(f"RSI {rsi:.1f} — overbought, potential pullback")
            else:
                reasons.append(f"RSI {rsi:.1f} — neutral zone")

        # Momentum
        if pct is not None:
            if pct > 0.01:
                score += 0.5
                reasons.append(f"Positive momentum: +{pct*100:.2f}%")
            elif pct < -0.01:
                score -= 0.5
                reasons.append(f"Negative momentum: {pct*100:.2f}%")

        # Volume
        if vol is not None:
            if vol > 1.5:
                score += 0.5
                reasons.append(f"High volume: {vol:.1f}x average — strong conviction")
            elif vol < 0.5:
                reasons.append(f"Low volume: {vol:.1f}x average — weak conviction")

    # Sentiment
    if sentiment > 0.2:
        score += 1.0
        reasons.append(f"Positive news sentiment: {sentiment:.3f}")
    elif sentiment < -0.2:
        score -= 1.0
        reasons.append(f"Negative news sentiment: {sentiment:.3f}")
    else:
        reasons.append(f"Neutral news sentiment: {sentiment:.3f}")

    # Signal
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
        "ticker":         ticker,
        "signal":         signal,
        "confidence":     round(confidence, 2),
        "score":          round(score, 2),
        "sentiment":      sentiment,
        "price_features": features,
        "reasons":        reasons,
    }