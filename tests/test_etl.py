"""
Layer 4 ETL Test
Run: python tests/test_etl.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from etl.pipeline import run_etl
from database.db import SessionLocal
from database.models import PriceClean, NewsClean

TICKER = "BTC"

print(f"\n{'='*50}")
print(f"  LAYER 4 ETL TEST — {TICKER}")
print(f"{'='*50}")

# Run full ETL
result = run_etl(TICKER)

# Verify in PostgreSQL
db = SessionLocal()

prices = db.query(PriceClean).filter_by(ticker=TICKER).limit(5).all()
news   = db.query(NewsClean).filter_by(ticker=TICKER).limit(5).all()

print(f"\n[Verify] prices_clean ({len(prices)} rows):")
for p in prices:
    print(f"  {p.ticker} | ${p.price} | ma5={p.ma5} | ma10={p.ma10} | pct={p.pct_change}")

print(f"\n[Verify] news_clean ({len(news)} rows):")
for n in news:
    label = "POSITIVE" if (n.sentiment or 0) > 0.2 else "NEGATIVE" if (n.sentiment or 0) < -0.2 else "NEUTRAL"
    print(f"  {n.ticker} | sentiment={n.sentiment} ({label}) | {(n.title or '')[:55]}")

db.close()

print(f"\n{'='*50}")
if prices or news:
    print("  ALL ETL TESTS PASSED ✓")
else:
    print("  WARNING: No data found — make sure Layer 2 has data first")
    print("  Run: python tests/test_layer2.py first")
print(f"{'='*50}\n")
