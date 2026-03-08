from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date,
    Numeric, BigInteger, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="portfolio")


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), unique=True, nullable=False)
    name = Column(String(200))
    asset_type = Column(String(20), default="stock")
    currency = Column(String(5), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="instrument")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    transaction_type = Column(String(10), nullable=False)  # "buy" or "sell"
    quantity = Column(Numeric(18, 8), nullable=False)
    price_per_unit = Column(Numeric(18, 6), nullable=False)
    fees = Column(Numeric(10, 4), default=0)
    transaction_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="transactions")
    instrument = relationship("Instrument", back_populates="transactions")


class PriceCache(Base):
    __tablename__ = "price_cache"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    price_date = Column(Date, nullable=False)
    open = Column(Numeric(18, 6))
    high = Column(Numeric(18, 6))
    low = Column(Numeric(18, 6))
    close = Column(Numeric(18, 6))
    volume = Column(BigInteger)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("ticker", "price_date"),)
