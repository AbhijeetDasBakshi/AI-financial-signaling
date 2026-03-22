from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, Text
from sqlalchemy.sql import func
from database.db import Base


class Price(Base):
    """Raw prices from Yahoo Finance — Layer 2."""
    __tablename__ = "prices"

    id         = Column(Integer, primary_key=True, index=True)
    ticker     = Column(String(10), nullable=False, index=True)
    price      = Column(Float, nullable=False)
    open       = Column(Float)
    high       = Column(Float)
    low        = Column(Float)
    volume     = Column(BigInteger)
    timestamp  = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PriceClean(Base):
    """Transformed prices with features — Layer 4 ETL output."""
    __tablename__ = "prices_clean"

    id               = Column(Integer, primary_key=True, index=True)
    ticker           = Column(String(10), nullable=False, index=True)
    price            = Column(Float, nullable=False)
    open             = Column(Float)
    high             = Column(Float)
    low              = Column(Float)
    volume           = Column(BigInteger)
    pct_change       = Column(Float)   # % change from previous close
    ma5              = Column(Float)   # 5-period moving average
    ma10             = Column(Float)   # 10-period moving average
    daily_range      = Column(Float)   # high - low
    price_normalized = Column(Float)   # min-max scaled 0-1
    timestamp        = Column(DateTime(timezone=True), nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class NewsClean(Base):
    """Cleaned news with VADER sentiment — Layer 4 ETL output."""
    __tablename__ = "news_clean"

    id           = Column(Integer, primary_key=True, index=True)
    ticker       = Column(String(10), nullable=False, index=True)
    title        = Column(Text)
    source       = Column(String(100))
    url          = Column(Text)
    published_at = Column(String(50))
    ingested_at  = Column(String(50))
    sentiment    = Column(Float)       # VADER compound score -1 to +1
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
