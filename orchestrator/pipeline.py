from sqlalchemy.orm import Session
from api.controllers import price_controller, news_controller
from etl.transform.transform_prices import transform_prices
from etl.transform.transform_news import transform_news
from etl.load.load_to_postgres import load_prices, load_news
from etl.extract.extract_prices import extract_prices


def run_pipeline(ticker: str, db: Session):
    ticker = ticker.upper()

    # ─── 1. Fetch + Store Price (Layer 2) ───────────────────
    price_record = price_controller.fetch_and_store_price(ticker, db)

    price_data = None
    if price_record:
        price_data = {
            "price":     price_record.price,
            "timestamp": str(price_record.timestamp)
        }

    # ─── 2. Fetch + Store News (Layer 2) ────────────────────
    news_fetch = news_controller.fetch_and_store_news(ticker, limit=5)

    # ─── 3. Sentiment Scoring (Layer 3) ─────────────────────
    sentiment_result = news_controller.get_news_with_sentiment(ticker, limit=5)

    avg_sentiment = None
    articles = []

    if sentiment_result:
        avg_sentiment = sentiment_result.get("average_sentiment")
        articles      = sentiment_result.get("articles", [])

    # ─── 4. ETL — Transform + Load (Layer 4) ────────────────

    # Transform + load news into news_clean
    if articles:
        transformed_news = transform_news(articles)
        load_news(transformed_news)

    # Transform + load prices into prices_clean
    raw_prices = extract_prices(ticker)
    if raw_prices:
        transformed_prices = transform_prices(raw_prices)
        load_prices(transformed_prices)

    # ─── 5. Signal Logic ─────────────────────────────────────
    signal     = "HOLD"
    confidence = 0.5

    if avg_sentiment is not None:
        if avg_sentiment > 0.2:
            signal     = "BUY"
            confidence = min(0.5 + avg_sentiment, 0.95)
        elif avg_sentiment < -0.2:
            signal     = "SELL"
            confidence = min(0.5 + abs(avg_sentiment), 0.95)

    # ─── 6. Final Response ───────────────────────────────────
    return {
        "ticker":           ticker,
        "price":            price_data,
        "news_fetched":     news_fetch.get("fetched", 0),
        "news_stored":      news_fetch.get("stored", 0),
        "average_sentiment": avg_sentiment,
        "signal":           signal,
        "confidence":       round(confidence, 2),
        "etl_ran":          True,
        "articles_sample":  articles[:3]
    }