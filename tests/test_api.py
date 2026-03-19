"""
Layer 3 Test — FastAPI endpoints
Run server first: uvicorn main:app --reload
Then run this:   python tests/test_api.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests

BASE_URL = "http://localhost:8000"
TICKER   = "AAPL"


def test_root():
    print("\n[1] Testing root endpoint...")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
    print("    GET / → OK")


def test_ingest():
    print("\n[2] Testing full ingest pipeline...")
    r = requests.get(f"{BASE_URL}/ingest/{TICKER}")
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == TICKER
    assert data["price"]["price"] is not None
    print(f"    GET /ingest/{TICKER} → OK")
    print(f"    Price:  ${data['price']['price']}")
    print(f"    News fetched:  {data['news']['fetched']}")
    print(f"    News stored:   {data['news']['stored']}")


def test_fetch_price():
    print("\n[3] Testing price fetch...")
    r = requests.get(f"{BASE_URL}/price/fetch", params={"ticker": TICKER})
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == TICKER
    assert data["price"] > 0
    print(f"    GET /price/fetch?ticker={TICKER} → OK")
    print(f"    Price: ${data['price']} | High: ${data['high']} | Low: ${data['low']}")


def test_price_history():
    print("\n[4] Testing price history...")
    r = requests.get(f"{BASE_URL}/price/history", params={"ticker": TICKER, "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    print(f"    GET /price/history?ticker={TICKER} → OK")
    print(f"    Records found: {len(data)}")
    for p in data:
        print(f"    - ${p['price']} at {p['timestamp']}")


def test_fetch_news():
    print("\n[5] Testing news fetch...")
    r = requests.get(f"{BASE_URL}/news/fetch", params={"ticker": TICKER, "limit": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == TICKER
    print(f"    GET /news/fetch?ticker={TICKER} → OK")
    print(f"    Fetched: {data['fetched']} | Stored: {data['stored']}")


def test_latest_news():
    print("\n[6] Testing latest news from MongoDB...")
    r = requests.get(f"{BASE_URL}/news/latest", params={"ticker": TICKER, "limit": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == TICKER
    print(f"    GET /news/latest?ticker={TICKER} → OK")
    print(f"    Articles found: {data['count']}")
    for a in data["articles"]:
        print(f"    - {a.get('title', 'no title')[:60]}")


if __name__ == "__main__":
    print("=" * 50)
    print("  LAYER 3 TEST — FastAPI Endpoints")
    print("=" * 50)

    try:
        test_root()
        test_ingest()
        test_fetch_price()
        test_price_history()
        test_fetch_news()
        test_latest_news()

        print("\n" + "=" * 50)
        print("  ALL TESTS PASSED ✓")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n  ASSERTION FAILED: {e}")
    except requests.exceptions.ConnectionError:
        print("\n  ERROR: Server not running.")
        print("  Start it with: uvicorn main:app --reload")