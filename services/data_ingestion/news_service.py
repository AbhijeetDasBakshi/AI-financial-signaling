import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from newsdataapi import NewsDataApiClient

load_dotenv()


class NewsService:

    def __init__(self):
        self.api = NewsDataApiClient(apikey=os.getenv("NEWSDATA_API_KEY"))
        self.last_called = {}

    def should_call_api(self, ticker):
        now = time.time()
        if ticker in self.last_called:
            if now - self.last_called[ticker] < 300:
                return False
        self.last_called[ticker] = now
        return True

    def load_cached_news(self, ticker):
        file_path = f"data/raw/news_{ticker}.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return None

    def save_news(self, ticker, data):
        os.makedirs("data/raw", exist_ok=True)
        file_path = f"data/raw/news_{ticker}.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

    def get_news(self, ticker, limit=5):
        cached_data = self.load_cached_news(ticker)
        if cached_data:
            print("Using cached news...")
            return cached_data

        if not self.should_call_api(ticker):
            print("Cooldown active. Skipping API call.")
            return []

        news_data = []

        try:
            response = self.api.news_api(
                q=ticker,
                language="en",
                size=limit
            )

            if response.get("status") != "success":
                print("[NewsService ERROR]: API limit or failure")
                return []

            articles = response.get("results", [])

            for article in articles:
                news_data.append({
                    "ticker": ticker,
                    "title": article.get("title"),
                    "source": article.get("source_id"),
                    "url": article.get("link"),
                    "published_at": article.get("pubDate"),
                    "raw_json": article,                          # store full response for MongoDB
                    "timestamp": datetime.now(timezone.utc).isoformat()  # BUG FIX
                })

            self.save_news(ticker, news_data)

        except Exception as e:
            print(f"[NewsService ERROR]: {e}")

        return news_data
