"""
Backtest API Route — Layer 5b
GET /backtest/?ticker=NVDA&period=6mo

Standalone endpoint: runs backtesting independently of the live pipeline.
For integrated backtest results, use POST /analyze/ which includes
a backtest_summary in the orchestrator output.
"""
from fastapi import APIRouter, Query

from backtesting.report import generate_report

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.get("/")
def backtest_ticker(
    ticker:      str  = Query(...,     description="Stock ticker e.g. NVDA"),
    period:      str  = Query("6mo",   description="Lookback period: 1mo, 3mo, 6mo, 1y, 2y"),
    include_log: bool = Query(False,   description="Include full per-day signal log"),
):
    """
    Replay historical signals and measure performance.

    Returns:
        win_rate, total_return, sharpe_ratio, max_drawdown, signals_tested,
        accuracy_by_signal, best_rule, worst_rule, ml diagnostics.

    Set include_log=true to get the full signal audit trail
    (one entry per trading day) for ML retraining analysis.
    """
    return generate_report(
        ticker=ticker,
        period=period,
        include_log=include_log,
    )