from fastapi import APIRouter, HTTPException
from api.controllers import news_controller

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/fetch")
def fetch_news(ticker: str, limit: int = 5):
    """Fetch news from NewsData API and store in MongoDB."""
    result = news_controller.fetch_and_store_news(ticker, limit)
    return {"ticker": ticker, **result}


@router.get("/latest")
def latest_news(ticker: str, limit: int = 10):
    """Get stored news from MongoDB."""
    articles = news_controller.get_stored_news(ticker, limit)
    if not articles:
        raise HTTPException(status_code=404, detail=f"No news found for {ticker}")
    return {"ticker": ticker, "count": len(articles), "articles": articles}
