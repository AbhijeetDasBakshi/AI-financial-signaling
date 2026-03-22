import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import SessionLocal
from database.models import PriceClean, NewsClean


def load_prices(transformed: list[dict]) -> int:
    if not transformed:
        return 0

    db = SessionLocal()
    inserted = 0
    try:
        for row in transformed:
            record = PriceClean(
                ticker           = row["ticker"],
                price            = row["price"],
                open             = row.get("open"),
                high             = row.get("high"),
                low              = row.get("low"),
                volume           = row.get("volume"),
                pct_change       = row.get("pct_change"),
                ma5              = row.get("ma5"),
                ma10             = row.get("ma10"),
                daily_range      = row.get("daily_range"),
                price_normalized = row.get("price_normalized"),
                timestamp        = row["timestamp"],
            )
            db.add(record)
            inserted += 1
        db.commit()
        print(f"[Load] {inserted} records → prices_clean")
    except Exception as e:
        db.rollback()
        print(f"[Load ERROR] prices: {e}")
    finally:
        db.close()
    return inserted


def load_news(transformed: list[dict]) -> int:
    if not transformed:
        return 0

    db = SessionLocal()
    inserted = 0
    try:
        for row in transformed:
            # Skip duplicates by URL
            if db.query(NewsClean).filter_by(url=row.get("url")).first():
                continue
            record = NewsClean(
                ticker       = row.get("ticker"),
                title        = row.get("title"),
                source       = row.get("source"),
                url          = row.get("url"),
                published_at = str(row.get("published_at", "")),
                ingested_at  = str(row.get("ingested_at", "")),
                sentiment    = row.get("sentiment"),
            )
            db.add(record)
            inserted += 1
        db.commit()
        print(f"[Load] {inserted} articles → news_clean")
    except Exception as e:
        db.rollback()
        print(f"[Load ERROR] news: {e}")
    finally:
        db.close()
    return inserted
