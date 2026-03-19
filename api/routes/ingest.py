from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from api.controllers import price_controller, news_controller

router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.get("/{ticker}")
def ingest_all(ticker: str, db: Session = Depends(get_db)):
    """
    Trigger full pipeline for a ticker:
    fetch price + news → store in PostgreSQL + MongoDB → return summary
    """
    ticker = ticker.upper()

    # Price
    price_record = price_controller.fetch_and_store_price(ticker, db)
    price_result = {
        "price":     price_record.price if price_record else None,
        "timestamp": str(price_record.timestamp) if price_record else None,
        "stored":    price_record is not None,
    }

    # News
    news_result = news_controller.fetch_and_store_news(ticker, limit=5)

    return {
        "ticker": ticker,
        "price":  price_result,
        "news":   news_result,
    }
