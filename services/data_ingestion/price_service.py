import yfinance as yf
from datetime import datetime, timezone


class PriceService:

    def get_stock_price(self, ticker: str):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")

            if data.empty:
                return None

            latest = data.iloc[-1]

            return {
                "ticker": ticker,
                "price":  float(latest["Close"]),
                "open":   float(latest["Open"]),
                "high":   float(latest["High"]),
                "low":    float(latest["Low"]),
                "volume": int(latest["Volume"]),
                "timestamp": datetime.now(timezone.utc).isoformat()  # BUG FIX
            }

        except Exception as e:
            print(f"[PriceService ERROR]: {e}")
            return None
