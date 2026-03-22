from services.data_ingestion.news_service import NewsService
from services.storage.storage_service import StorageService
from services.sentiment.sentiment_service import SentimentService

news_svc      = NewsService()
storage_svc   = StorageService()
sentiment_svc = SentimentService()


# ─── FETCH + STORE RAW NEWS ───────────────────────────────────────────────

def fetch_and_store_news(ticker: str, limit: int = 5):
    """
    Fetch news from API and store in MongoDB
    """
    articles = news_svc.get_news(ticker.upper(), limit=limit)
    stored   = storage_svc.store_news(articles)

    return {
        "ticker": ticker,
        "fetched": len(articles),
        "stored": stored
    }


# ─── GET RAW NEWS ─────────────────────────────────────────────────────────

def get_stored_news(ticker: str, limit: int = 10):
    """
    Fetch raw stored news from MongoDB
    """
    return storage_svc.get_news(ticker.upper(), limit=limit)


# ─── GET NEWS WITH SENTIMENT (NO STORAGE) ──────────────────────────────────

def get_news_with_sentiment(ticker: str, limit: int = 10):
    """
    Fetch news + compute sentiment (on-demand)
    """
    articles = storage_svc.get_news(ticker.upper(), limit=limit)

    if not articles:
        return []

    # Compute sentiment
    articles = sentiment_svc.analyze_batch(articles)

    avg_sentiment = sentiment_svc.get_average_sentiment(articles)

    return {
        "ticker": ticker,
        "average_sentiment": avg_sentiment,
        "count": len(articles),
        "articles": articles
    }


# ─── COMPUTE + STORE SENTIMENT ────────────────────────────────────────────

def compute_and_store_sentiment(ticker: str, limit: int = 10):
    """
    Compute sentiment and store it in MongoDB
    """
    articles = storage_svc.get_news(ticker.upper(), limit=limit)

    if not articles:
        return []

    # Compute sentiment
    articles = sentiment_svc.analyze_batch(articles)

    # Store sentiment in DB
    updated_count = storage_svc.update_sentiment(articles)

    avg_sentiment = sentiment_svc.get_average_sentiment(articles)

    return {
        "ticker": ticker,
        "average_sentiment": avg_sentiment,
        "updated": updated_count
    }