from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import List, Dict


class SentimentService:
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze_text(self, text: str) -> float:
        """
        Returns sentiment score between -1 to +1
        """
        if not text:
            return 0.0
        
        score = self.analyzer.polarity_scores(text)
        return score["compound"]

    def analyze_article(self, article: Dict) -> Dict:
        title = article.get("title", "")
        article["sentiment"] = self.analyze_text(title)  # always re-score
        return article

    def analyze_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Adds sentiment to list of articles
        """
        return [self.analyze_article(a) for a in articles]

    def get_average_sentiment(self, articles: List[Dict]) -> float:
        """
        Returns average sentiment score
        """
        if not articles:
            return 0.0
        
        sentiments = [a.get("sentiment", 0) for a in articles]
        return sum(sentiments) / len(sentiments)