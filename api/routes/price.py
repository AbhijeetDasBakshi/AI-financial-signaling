from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from api.controllers import price_controller

router = APIRouter(prefix="/price", tags=["Price"])


@router.get("/fetch")
def fetch_price(ticker: str, db: Session = Depends(get_db)):
    """Fetch live price from Yahoo Finance and store in PostgreSQL."""
    record = price_controller.fetch_and_store_price(ticker, db)
    if not record:
        raise HTTPException(status_code=404, detail=f"Could not fetch price for {ticker}")
    return {
        "ticker":    record.ticker,
        "price":     record.price,
        "open":      record.open,
        "high":      record.high,
        "low":       record.low,
        "volume":    record.volume,
        "timestamp": record.timestamp,
    }


@router.get("/history")
def price_history(ticker: str, limit: int = 20, db: Session = Depends(get_db)):
    """Get stored price history from PostgreSQL."""
    records = price_controller.get_price_history(ticker, db, limit)
    if not records:
        raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")
    return [
        {
            "ticker":    r.ticker,
            "price":     r.price,
            "timestamp": r.timestamp,
        }
        for r in records
    ]