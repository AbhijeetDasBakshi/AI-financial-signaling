from fastapi import APIRouter, HTTPException
from api.controllers import news_controller

router = APIRouter(prefix="/news", tags=["News"])


# ─── FETCH + STORE NEWS ───────────────────────────────────────────────

@router.get("/fetch")
def fetch_news(ticker: str, limit: int = 5):
    """
    Fetch news from API and store in MongoDB
    """
    result = news_controller.fetch_and_store_news(ticker, limit)
    return result


# ─── GET RAW NEWS ─────────────────────────────────────────────────────

@router.get("/latest")
def latest_news(ticker: str, limit: int = 10):
    """
    Get stored news from MongoDB
    """
    articles = news_controller.get_stored_news(ticker, limit)

    if not articles:
        raise HTTPException(
            status_code=404,
            detail=f"No news found for {ticker}"
        )

    return {
        "ticker": ticker,
        "count": len(articles),
        "articles": articles
    }


# ─── GET NEWS WITH SENTIMENT (NO STORAGE) ─────────────────────────────

@router.get("/sentiment")
def news_sentiment(ticker: str, limit: int = 10):
    """
    Compute sentiment on demand (no DB storage)
    """
    result = news_controller.get_news_with_sentiment(ticker, limit)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No news found for {ticker}"
        )

    return result


# ─── COMPUTE + STORE SENTIMENT ────────────────────────────────────────

@router.post("/sentiment/store")
def store_sentiment(ticker: str, limit: int = 10):
    """
    Compute sentiment and store in MongoDB
    """
    result = news_controller.compute_and_store_sentiment(ticker, limit)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No news found for {ticker}"
        )

    return result