"""
Portfolio route — compare signals across multiple tickers.
GET /portfolio?tickers=NVDA,AAPL,MSFT,BTC
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from orchestrator.pipeline import run_pipeline

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/")
def get_portfolio_signals(tickers: str, db: Session = Depends(get_db)):
    """
    Run full pipeline for multiple tickers and return comparison.
    tickers = comma-separated list e.g. NVDA,AAPL,MSFT,BTC
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    if not ticker_list:
        return {"error": "No tickers provided"}

    if len(ticker_list) > 5:
        return {"error": "Maximum 5 tickers per request"}

    results  = []
    buy_list = []
    hold_list = []
    sell_list = []

    for ticker in ticker_list:
        try:
            result = run_pipeline(ticker, db, explain=False)  # skip LLM for speed
            results.append({
                "ticker":     ticker,
                "price":      result.get("price"),
                "signal":     result.get("signal"),
                "confidence": result.get("confidence"),
                "score":      result.get("score"),
                "sentiment":  result.get("average_sentiment"),
                "reasons":    result.get("reasons", [])[:2],  # top 2 reasons only
            })

            signal = result.get("signal")
            if signal == "BUY":
                buy_list.append(ticker)
            elif signal == "SELL":
                sell_list.append(ticker)
            else:
                hold_list.append(ticker)

        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    # Sort by confidence descending
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return {
        "portfolio_summary": {
            "total":    len(ticker_list),
            "buy":      buy_list,
            "hold":     hold_list,
            "sell":     sell_list,
            "top_pick": results[0]["ticker"] if results else None,
        },
        "tickers": results,
    }
