from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database.db import news_collection
from database.models import Price


class StorageService:

    # ─── MongoDB: store raw news ───────────────────────────────────────────────

    def store_news(self, news_items: list[dict]) -> int:
        """
        Insert news articles into MongoDB.
        Skips duplicates based on (ticker, url).
        Returns count of actually inserted documents.
        """
        if not news_items:
            return 0

        inserted = 0

        for item in news_items:
            # Avoid duplicates
            existing = news_collection.find_one({
                "ticker": item["ticker"],
                "url":    item.get("url")
            })

            if existing:
                print(f"[StorageService] Skipping duplicate: {item.get('url')}")
                continue

            doc = {
                "ticker":       item["ticker"],
                "title":        item.get("title"),
                "source":       item.get("source"),
                "url":          item.get("url"),
                "published_at": item.get("published_at"),
                "raw_json":     item.get("raw_json", {}),   # full API response
                "ingested_at":  datetime.now(timezone.utc).isoformat(),
            }

            news_collection.insert_one(doc)
            inserted += 1

        print(f"[StorageService] Stored {inserted} new article(s) in MongoDB")
        return inserted

    def get_news(self, ticker: str, limit: int = 10) -> list[dict]:
        """Fetch latest news for a ticker from MongoDB."""
        cursor = (
            news_collection
            .find({"ticker": ticker}, {"_id": 0})  # exclude Mongo _id
            .sort("ingested_at", -1)
            .limit(limit)
        )
        return list(cursor)

    # ─── PostgreSQL: store structured prices ──────────────────────────────────

    def store_price(self, price_data: dict, db: Session) -> Price:
        """
        Insert a price record into PostgreSQL.
        Returns the saved ORM object.
        """
        if not price_data:
            raise ValueError("price_data is empty")

        record = Price(
            ticker    = price_data["ticker"],
            price     = price_data["price"],
            open      = price_data.get("open"),
            high      = price_data.get("high"),
            low       = price_data.get("low"),
            volume    = price_data.get("volume"),
            timestamp = datetime.fromisoformat(price_data["timestamp"]),
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        print(f"[StorageService] Stored price for {record.ticker}: ${record.price}")
        return record

    def get_prices(self, ticker: str, db: Session, limit: int = 20) -> list[Price]:
        """Fetch latest price records for a ticker from PostgreSQL."""
        return (
            db.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(Price.timestamp.desc())
            .limit(limit)
            .all()
        )
