from sqlalchemy.orm import Session
from services.data_ingestion.price_service import PriceService
from services.storage.storage_service import StorageService

price_svc   = PriceService()
storage_svc = StorageService()


def fetch_and_store_price(ticker: str, db: Session):
    """Fetch live price and store in PostgreSQL. Returns saved record."""
    data = price_svc.get_stock_price(ticker.upper())
    if not data:
        return None
    return storage_svc.store_price(data, db)


def get_price_history(ticker: str, db: Session, limit: int = 20):
    """Read stored price history from PostgreSQL."""
    return storage_svc.get_prices(ticker.upper(), db, limit=limit)
