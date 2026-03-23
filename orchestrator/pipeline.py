"""
Orchestrator Pipeline — Layer 5 Upgraded.
Runs full pipeline per ticker:
1. Fetch + store price + news
2. ETL transform
3. Rule engine signal
4. ML classifier signal
5. Combined confidence scoring
6. Support/resistance price targets
7. LLM explanation
"""
from sqlalchemy.orm import Session
from api.controllers import price_controller, news_controller
from etl.transform.transform_prices import transform_prices
from etl.transform.transform_news import transform_news
from etl.load.load_to_postgres import load_prices, load_news
from etl.extract.extract_prices import extract_prices
from services.signal_engine.rule_engine import compute_signal, get_historical_features, _history_cache, get_average_sentiment
from services.signal_engine.ml_engine import train_and_predict
from services.signal_engine.confidence_engine import compute_combined_signal
from services.signal_engine.price_target import compute_price_targets
from services.signal_engine.llm_engine import get_llm_explanation
import os

ML_HISTORY_PERIOD = os.getenv("ML_HISTORY_PERIOD", "6mo")


def run_pipeline(ticker: str, db: Session, explain: bool = True) -> dict:
    ticker = ticker.upper()

    # ─── 1. Fetch + Store Price + News ───────────────────────
    price_record = price_controller.fetch_and_store_price(ticker, db)
    price_data   = None
    if price_record:
        price_data = {
            "price":     price_record.price,
            "timestamp": str(price_record.timestamp)
        }

    news_fetch       = news_controller.fetch_and_store_news(ticker, limit=5)
    sentiment_result = news_controller.get_news_with_sentiment(ticker, limit=5)

    avg_sentiment = None
    articles      = []
    if sentiment_result:
        avg_sentiment = sentiment_result.get("average_sentiment")
        articles      = sentiment_result.get("articles", [])

    # ─── 2. ETL ───────────────────────────────────────────────
    if articles:
        load_news(transform_news(articles))

    raw_prices = extract_prices(ticker)
    if raw_prices:
        load_prices(transform_prices(raw_prices))

    # ─── 3. Get historical records (cached 1hr) ───────────────
    from services.data_ingestion.price_service import PriceService
    import time
    price_svc = PriceService()
    now       = time.time()

    if ticker in _history_cache:
        _, hist_records = _history_cache[ticker]
    else:
        hist_records = price_svc.get_historical_prices(ticker, period=ML_HISTORY_PERIOD)
        _history_cache[ticker] = (now, hist_records)

    # ─── 4. Rule engine signal ────────────────────────────────
    rule_data = compute_signal(ticker, live_sentiment=avg_sentiment)

    # ─── 5. ML signal ─────────────────────────────────────────
    ml_result = train_and_predict(hist_records)

    # ─── 6. Combined confidence ───────────────────────────────
    rule_clean = {
        "signal": rule_data["signal"],
        "confidence": rule_data["confidence"]
    }

    ml_clean = {
        "signal": ml_result.get("ml_signal", "INSUFFICIENT_DATA"),
        "confidence": ml_result.get("ml_confidence", 0.5),
        "accuracy": ml_result.get("ml_accuracy"),
    }

    combined = compute_combined_signal(rule_clean, ml_clean)

    # ─── 7. Price targets ─────────────────────────────────────
    current_price = price_data["price"] if price_data else None

    targets = compute_price_targets(hist_records, current_price) if hist_records and current_price else None

    # ─── 8. LLM explanation ───────────────────────────────────
    explanation = None
    if explain:
        headlines = [a.get("title", "") for a in articles[:5] if a.get("title")]
        explanation = get_llm_explanation(
            ticker,
            {
                **rule_data,
                "signal": combined["signal"],          
                "confidence": combined["confidence"],  
            },
            headlines
        )

    # ─── 9. Final response ────────────────────────────────────
    return {
        "ticker":           ticker,
        "price":            price_data,
        "news_fetched":     news_fetch.get("fetched", 0),
        "news_stored":      news_fetch.get("stored", 0),
        "average_sentiment": avg_sentiment,

        # Signal
        "signal":           combined["signal"],
        "confidence":       combined["confidence"],
        "signals_agree":    combined["agreement"],
        "signal_note":      combined.get("note"),

        # Rule engine
        "rule_signal":      rule_data["signal"],
        "rule_confidence":  rule_data["confidence"],
        "rule_score":       rule_data["score"],
        "reasons":          rule_data["reasons"],

        # ML
        "ml_signal":        ml_result.get("ml_signal"),
        "ml_confidence":    ml_result.get("ml_confidence"),
        "ml_accuracy":      ml_result.get("ml_accuracy"),
        "ml_model":         ml_result.get("ml_model"),
        "feature_importance": ml_result.get("feature_importance", {}),

        # Price targets
        "price_targets":    targets,

        # LLM
        "explanation":      explanation,
        "etl_ran":          True,
        "articles_sample":  articles[:3],
    }