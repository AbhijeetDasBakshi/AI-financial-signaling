import yfinance as yf
from datetime import datetime, timezone


class PriceService:

    CRYPTO_MAP = {
        "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
        "BNB": "BNB-USD", "XRP": "XRP-USD", "ADA": "ADA-USD",
        "DOGE": "DOGE-USD", "DOT": "DOT-USD", "MATIC": "MATIC-USD",
        "AVAX": "AVAX-USD",
    }

    def get_stock_price(self, ticker: str):
        """Get latest single price — used for live storage."""
        try:
            ticker    = ticker.upper()
            yf_ticker = self.CRYPTO_MAP.get(ticker, ticker)
            stock     = yf.Ticker(yf_ticker)
            data      = stock.history(period="1d")

            if data.empty:
                print(f"[PriceService] No data for {ticker}")
                return None

            latest = data.iloc[-1]
            return {
                "ticker":    ticker,
                "price":     float(latest["Close"]),
                "open":      float(latest["Open"]),
                "high":      float(latest["High"]),
                "low":       float(latest["Low"]),
                "volume":    int(latest["Volume"]),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            print(f"[PriceService ERROR]: {e}")
            return None

    def get_historical_prices(self, ticker: str, period: str = "3mo") -> list[dict]:
        """
        Fetch historical OHLCV data from Yahoo Finance.

        Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
        Used to feed rule engine + LLM with rich context.
        """
        try:
            ticker    = ticker.upper()
            yf_ticker = self.CRYPTO_MAP.get(ticker, ticker)
            stock     = yf.Ticker(yf_ticker)
            data      = stock.history(period=period)

            if data.empty:
                print(f"[PriceService] No historical data for {ticker}")
                return []

            records = []
            for ts, row in data.iterrows():
                records.append({
                    "ticker":    ticker,
                    "price":     round(float(row["Close"]), 4),
                    "open":      round(float(row["Open"]), 4),
                    "high":      round(float(row["High"]), 4),
                    "low":       round(float(row["Low"]), 4),
                    "volume":    int(row["Volume"]),
                    "timestamp": ts.to_pydatetime(),
                })

            print(f"[PriceService] {len(records)} historical records for {ticker} ({period})")
            return records

        except Exception as e:
            print(f"[PriceService ERROR] historical: {e}")
            return []