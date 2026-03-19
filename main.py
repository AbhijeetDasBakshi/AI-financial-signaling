from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from services.data_ingestion.news_service import NewsService
from services.data_ingestion.price_service import PriceService
from services.storage.storage_service import StorageService

app = FastAPI(title="Financial Signaling")

news_svc    = NewsService()
price_svc   = PriceService()
storage_svc = StorageService()


@app.get("/ingest/news/{ticker}")
def ingest_news(ticker: str, limit: int = 5):
    """Fetch news from NewsData API and store in MongoDB."""
    news = news_svc.get_news(ticker.upper(), limit=limit)
    stored = storage_svc.store_news(news)
    return {"ticker": ticker, "fetched": len(news), "stored": stored}


@app.get("/ingest/price/{ticker}")
def ingest_price(ticker: str, db: Session = Depends(get_db)):
    """Fetch price from Yahoo Finance and store in PostgreSQL."""
    price = price_svc.get_stock_price(ticker.upper())
    if not price:
        return {"error": f"Could not fetch price for {ticker}"}
    record = storage_svc.store_price(price, db)
    return {"ticker": ticker, "price": record.price, "id": record.id}


@app.get("/news/{ticker}")
def get_news(ticker: str, limit: int = 10):
    """Read news from MongoDB."""
    return storage_svc.get_news(ticker.upper(), limit=limit)


@app.get("/prices/{ticker}")
def get_prices(ticker: str, limit: int = 20, db: Session = Depends(get_db)):
    """Read prices from PostgreSQL."""
    records = storage_svc.get_prices(ticker.upper(), db, limit=limit)
    return [
        {"id": r.id, "ticker": r.ticker, "price": r.price, "timestamp": r.timestamp}
        for r in records
    ]
