import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from newsdataapi import NewsDataApiClient

load_dotenv()


class NewsService:

    COOLDOWN_SECONDS = 30

    # Map ticker → better search term for NewsData API
    SEARCH_MAP = {
        # Stocks
        "AAPL":  "Apple",
        "NVDA":  "NVIDIA",
        "TSLA":  "Tesla",
        "MSFT":  "Microsoft",
        "GOOGL": "Google",
        "AMZN":  "Amazon",
        "META":  "Meta",
        "NFLX":  "Netflix",
        "AMD":   "AMD semiconductor",
        "INTC":  "Intel",
        "BABA":  "Alibaba",
        "UBER":  "Uber",

        # Crypto
        "BTC":   "Bitcoin",
        "ETH":   "Ethereum",
        "SOL":   "Solana",
        "BNB":   "Binance",
        "XRP":   "Ripple XRP",
        "ADA":   "Cardano",
        "DOGE":  "Dogecoin",
    }

    def __init__(self):
        self.api = NewsDataApiClient(apikey=os.getenv("NEWSDATA_API_KEY"))
        self.last_called = {}

    def get_search_term(self, ticker: str) -> str:
        """Return best search term for NewsData API."""
        return self.SEARCH_MAP.get(ticker.upper(), ticker.upper())

    def should_call_api(self, ticker):
        now = time.time()
        if ticker in self.last_called:
            if now - self.last_called[ticker] < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - (now - self.last_called[ticker]))
                print(f"[NewsService] Cooldown active. {remaining}s remaining.")
                return False
        self.last_called[ticker] = now
        return True

    def load_cached_news(self, ticker):
        file_path = f"data/raw/news_{ticker}.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                if data:
                    return data
        return None

    def save_news(self, ticker, data):
        os.makedirs("data/raw", exist_ok=True)
        file_path = f"data/raw/news_{ticker}.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

    def clear_cache(self, ticker):
        file_path = f"data/raw/news_{ticker}.json"
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[NewsService] Cache cleared for {ticker}")

    def get_news(self, ticker, limit=5):
        ticker = ticker.upper()

        cached_data = self.load_cached_news(ticker)
        if cached_data:
            print(f"[NewsService] Using cached news for {ticker}")
            return cached_data

        if not self.should_call_api(ticker):
            return []

        # Use company name for better results
        search_term = self.get_search_term(ticker)
        print(f"[NewsService] Searching '{search_term}' for ticker {ticker}")

        news_data = []

        try:
            response = self.api.news_api(
                q=search_term,
                language="en",
                size=limit,
                category="business,technology,top"
            )

            if response.get("status") != "success":
                print(f"[NewsService ERROR]: {response.get('results', {}).get('message', 'Unknown')}")
                return []

            articles = response.get("results", [])

            for article in articles:
                news_data.append({
                    "ticker":       ticker,
                    "search_term":  search_term,
                    "title":        article.get("title"),
                    "source":       article.get("source_id"),
                    "url":          article.get("link"),
                    "published_at": article.get("pubDate"),
                    "raw_json":     article,
                    "timestamp":    datetime.now(timezone.utc).isoformat()
                })

            self.save_news(ticker, news_data)
            print(f"[NewsService] Fetched {len(news_data)} articles for {ticker}")

        except Exception as e:
            print(f"[NewsService ERROR]: {e}")

        return news_data