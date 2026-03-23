from fastapi import APIRouter
from services.signal_engine.rule_engine import compute_signal
from services.signal_engine.llm_engine import get_llm_explanation
from database.db import news_collection

router = APIRouter(prefix="/signal", tags=["Signal"])


def get_news_headlines(ticker: str, limit: int = 5) -> list[str]:
    """Fetch recent headlines from MongoDB for LLM context."""
    cursor = (
        news_collection
        .find({"ticker": ticker.upper()}, {"_id": 0, "title": 1})
        .sort("ingested_at", -1)
        .limit(limit)
    )
    return [doc.get("title", "") for doc in cursor if doc.get("title")]


@router.get("/{ticker}")
def get_signal(ticker: str, explain: bool = True):
    """
    Get BUY/SELL/HOLD signal for a ticker.
    - Rule engine computes signal from price features + sentiment
    - LLM generates human explanation (set explain=false to skip)
    """
    ticker = ticker.upper()

    # Step 1 — rule-based signal
    signal_data = compute_signal(ticker)

    # Step 2 — LLM explanation (optional)
    explanation = None
    if explain:
        headlines   = get_news_headlines(ticker)
        explanation = get_llm_explanation(ticker, signal_data, headlines)

    return {
        "ticker":      ticker,
        "signal":      signal_data["signal"],
        "confidence":  signal_data["confidence"],
        "score":       signal_data["score"],
        "sentiment":   signal_data["sentiment"],
        "reasons":     signal_data["reasons"],
        "explanation": explanation,
        "price":       signal_data.get("price_features"),
    }
