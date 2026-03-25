from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database.db import get_db

from orchestrator.pipeline import run_pipeline

router = APIRouter(prefix="/analyze", tags=["Analyze"])


@router.post("/")
def analyze_stock(
    ticker:        str            = Query(...,   description="Stock ticker e.g. NVDA"),
    db:            Session        = Depends(get_db),
    run_backtest:  bool           = Query(None,  description="Override BACKTEST_ON_ANALYZE env var"),
):
    """
    Full pipeline:
    price + news + sentiment + signal + backtest summary

    The backtest_summary field in the response contains historical
    performance metrics for the generated signal strategy.

    To skip backtesting (faster response): ?run_backtest=false
    To force backtesting even if disabled in .env: ?run_backtest=true
    For the full backtest report with signal log: GET /backtest/?ticker=NVDA
    """
    result = run_pipeline(ticker, db, run_backtest=run_backtest)
    return result