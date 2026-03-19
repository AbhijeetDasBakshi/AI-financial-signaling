from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime
from sqlalchemy.sql import func
from database.db import Base


class Price(Base):
    """Structured price data — one row per ticker per fetch."""
    __tablename__ = "prices"

    id        = Column(Integer, primary_key=True, index=True)
    ticker    = Column(String(10), nullable=False, index=True)
    price     = Column(Float, nullable=False)
    open      = Column(Float)
    high      = Column(Float)
    low       = Column(Float)
    volume    = Column(BigInteger)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
