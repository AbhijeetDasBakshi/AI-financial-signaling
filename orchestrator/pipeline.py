
from sqlalchemy.orm import Session

from api.controllers import price_controller, news_controller


def run_pipeline(ticker: str, db: Session):
    ticker = ticker.upper()

    # ─── 1. Fetch + Store Price ─────────────────────────────
    price_record = price_controller.fetch_and_store_price(ticker, db)

    price_data = None
    if price_record:
        price_data = {
            "price": price_record.price,
            "timestamp": str(price_record.timestamp)
        }

    # ─── 2. Fetch + Store News ──────────────────────────────
    news_fetch = news_controller.fetch_and_store_news(ticker, limit=5)

    # ─── 3. Compute Sentiment (ON DEMAND) ───────────────────
    sentiment_result = news_controller.get_news_with_sentiment(ticker, limit=5)

    avg_sentiment = None
    articles = []

    if sentiment_result:
        avg_sentiment = sentiment_result.get("average_sentiment")
        articles = sentiment_result.get("articles", [])

    # ─── 4. SIMPLE SIGNAL LOGIC (TEMP ML) ───────────────────
    signal = "HOLD"
    confidence = 0.5

    if avg_sentiment is not None:
        if avg_sentiment > 0.2:
            signal = "BUY"
            confidence = min(0.5 + avg_sentiment, 0.95)
        elif avg_sentiment < -0.2:
            signal = "SELL"
            confidence = min(0.5 + abs(avg_sentiment), 0.95)

    # ─── 5. FINAL RESPONSE ─────────────────────────────────
    return {
        "ticker": ticker,
        "price": price_data,
        "news_fetched": news_fetch.get("fetched", 0),
        "news_stored": news_fetch.get("stored", 0),
        "average_sentiment": avg_sentiment,
        "signal": signal,
        "confidence": round(confidence, 2),
        "articles_sample": articles[:3]  # limit response size
    }
