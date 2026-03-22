"""
ETL Pipeline — Layer 4
Reads raw data → transforms → loads into clean tables.
This is separate from orchestrator/pipeline.py which handles
live ingestion + signal generation.

Usage:
    python etl/pipeline.py BTC
    python etl/pipeline.py AAPL
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from etl.extract.extract_news    import extract_news
from etl.extract.extract_prices  import extract_prices
from etl.transform.transform_news   import transform_news
from etl.transform.transform_prices import transform_prices
from etl.load.load_to_postgres   import load_news, load_prices


def run_etl(ticker: str) -> dict:
    ticker = ticker.upper()
    print(f"\n{'='*50}")
    print(f"  ETL PIPELINE — {ticker}")
    print(f"{'='*50}")

    # ── NEWS: MongoDB → clean → news_clean table ──────
    print("\n--- NEWS ---")
    raw_news         = extract_news(ticker)
    transformed_news = transform_news(raw_news)
    loaded_news      = load_news(transformed_news)

    # ── PRICES: PostgreSQL → features → prices_clean ──
    print("\n--- PRICES ---")
    raw_prices         = extract_prices(ticker)
    transformed_prices = transform_prices(raw_prices)
    loaded_prices      = load_prices(transformed_prices)

    result = {
        "ticker":        ticker,
        "news_loaded":   loaded_news,
        "prices_loaded": loaded_prices,
    }

    print(f"\n{'='*50}")
    print(f"  ETL COMPLETE")
    print(f"  News:   {len(raw_news)} → {loaded_news} loaded into news_clean")
    print(f"  Prices: {len(raw_prices)} → {loaded_prices} loaded into prices_clean")
    print(f"{'='*50}\n")

    return result


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    run_etl(ticker)
