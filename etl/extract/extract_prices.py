import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import SessionLocal
from database.models import Price


def extract_prices(ticker: str, limit: int = 200) -> list[dict]:
    db = SessionLocal()
    try:
        records = (
            db.query(Price)
            .filter(Price.ticker == ticker.upper())
            .order_by(Price.timestamp.desc())
            .limit(limit)
            .all()
        )
        data = [
            {
                "ticker":    r.ticker,
                "price":     r.price,
                "open":      r.open,
                "high":      r.high,
                "low":       r.low,
                "volume":    r.volume,
                "timestamp": r.timestamp,
            }
            for r in records
        ]
        print(f"[Extract] {len(data)} price records for {ticker}")
        return data
    finally:
        db.close()
