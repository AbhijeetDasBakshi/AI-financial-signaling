"""
Layer 2 Test — run from project root:
    python test_layer2.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



from services.data_ingestion.news_service import NewsService
from services.data_ingestion.price_service import PriceService
from services.storage.storage_service import StorageService
from database.db import SessionLocal

news_svc    = NewsService()
price_svc   = PriceService()
storage_svc = StorageService()
db          = SessionLocal()

TICKER = "AAPL"

print("\n" + "="*50)
print(f"  LAYER 2 TEST — {TICKER}")
print("="*50)

# ─── Test 1: Fetch news ───────────────────────────────
print("\n[1] Fetching news from NewsData API...")
news = news_svc.get_news(TICKER, limit=3)
print(f"    Fetched: {len(news)} articles")

# ─── Test 2: Store news in MongoDB ───────────────────
print("\n[2] Storing news in MongoDB...")
stored = storage_svc.store_news(news)
print(f"    Stored: {stored} articles")

# ─── Test 3: Read news back from MongoDB ─────────────
print("\n[3] Reading news back from MongoDB...")
saved_news = storage_svc.get_news(TICKER, limit=3)
print(f"    Found: {len(saved_news)} articles in MongoDB")
for n in saved_news:
    print(f"    - {n.get('title', 'no title')[:60]}")

# ─── Test 4: Fetch price ──────────────────────────────
print("\n[4] Fetching price from Yahoo Finance...")
price = price_svc.get_stock_price(TICKER)
print(f"    Price: ${price['price']} at {price['timestamp']}")

# ─── Test 5: Store price in PostgreSQL ───────────────
print("\n[5] Storing price in PostgreSQL...")
record = storage_svc.store_price(price, db)
print(f"    Stored: ID={record.id} ticker={record.ticker} price=${record.price}")

# ─── Test 6: Read price back from PostgreSQL ─────────
print("\n[6] Reading price back from PostgreSQL...")
saved_prices = storage_svc.get_prices(TICKER, db, limit=3)
print(f"    Found: {len(saved_prices)} records in PostgreSQL")
for p in saved_prices:
    print(f"    - {p.ticker}: ${p.price} at {p.timestamp}")

print("\n" + "="*50)
print("  ALL TESTS PASSED ✓" if saved_prices else "  SOMETHING FAILED ✗")
print("="*50 + "\n")

db.close()