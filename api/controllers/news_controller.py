from services.data_ingestion.news_service import NewsService
from services.storage.storage_service import StorageService

news_svc    = NewsService()
storage_svc = StorageService()


def fetch_and_store_news(ticker: str, limit: int = 5):
    """Fetch news from NewsData API and store in MongoDB. Returns stored count."""
    articles = news_svc.get_news(ticker.upper(), limit=limit)
    stored   = storage_svc.store_news(articles)
    return {"fetched": len(articles), "stored": stored}


def get_stored_news(ticker: str, limit: int = 10):
    """Read stored news from MongoDB."""
    return storage_svc.get_news(ticker.upper(), limit=limit)
