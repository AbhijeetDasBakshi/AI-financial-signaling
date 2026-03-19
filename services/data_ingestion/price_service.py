import yfinance as yf
from datetime import datetime

class PriceService:

    def get_stock_price(self, ticker: str):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")

            if data.empty:
                return None

            return {
                "ticker": ticker,
                "price": float(data["Close"].iloc[-1]),
                "timestamp": datetime.timezone.utc()
            }

        except Exception as e:
            print(f"[PriceService ERROR]: {e}")
            return None