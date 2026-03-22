import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import news_collection


def extract_news(ticker: str, limit: int = 100) -> list[dict]:
    cursor = (
        news_collection
        .find({"ticker": ticker.upper()}, {"_id": 0})
        .sort("ingested_at", -1)
        .limit(limit)
    )
    articles = list(cursor)
    print(f"[Extract] {len(articles)} news articles for {ticker}")
    return articles
