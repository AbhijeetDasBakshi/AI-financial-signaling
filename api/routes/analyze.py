from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db

from orchestrator.pipeline import run_pipeline

router = APIRouter(prefix="/analyze", tags=["Analyze"])


@router.post("/")
def analyze_stock(ticker: str, db: Session = Depends(get_db)):
    """
    Full pipeline:
    price + news + sentiment + signal
    """
    result = run_pipeline(ticker, db)
    return result