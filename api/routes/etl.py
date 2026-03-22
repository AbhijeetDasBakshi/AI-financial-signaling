from fastapi import APIRouter
from etl.pipeline import run_etl

router = APIRouter(prefix="/etl", tags=["ETL"])


@router.get("/run/{ticker}")
def run_etl_pipeline(ticker: str):
    """
    Trigger ETL pipeline for a ticker.
    Reads raw data → transforms → loads into prices_clean + news_clean tables.
    """
    return run_etl(ticker.upper())
