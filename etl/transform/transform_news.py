"""
Transform raw news from MongoDB:
- Clean title text
- Score sentiment using your existing SentimentService (VADER)
"""
import re
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.sentiment.sentiment_service import SentimentService

sentiment_svc = SentimentService()


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s.,!?'-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def transform_news(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    cleaned = []
    for article in articles:
        try:
            clean_title = clean_text(article.get("title", ""))
            # Always re-score — never trust stored 0
            sentiment = sentiment_svc.analyze_text(clean_title)
            cleaned.append({
                **article,
                "title":     clean_title,
                "sentiment": sentiment   # overwrite stored value
            })
        except Exception as e:
            print(f"[Transform] Skipping: {e}")

    print(f"[Transform] {len(cleaned)} articles scored")
    return cleaned