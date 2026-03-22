import yfinance as yf
from datetime import datetime, timezone


class PriceService:

    # Crypto tickers need -USD suffix for Yahoo Finance
    # All stock tickers (AAPL, NVDA, TSLA, GOOGL etc.) work as-is
    CRYPTO_MAP = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "BNB": "BNB-USD",
        "XRP": "XRP-USD",
        "ADA": "ADA-USD",
        "DOGE": "DOGE-USD",
        "DOT": "DOT-USD",
        "MATIC": "MATIC-USD",
        "AVAX": "AVAX-USD",
    }

    def get_stock_price(self, ticker: str):
        try:
            ticker = ticker.upper()

            # Crypto needs -USD, stocks work as-is
            yf_ticker = self.CRYPTO_MAP.get(ticker, ticker)

            stock = yf.Ticker(yf_ticker)
            data = stock.history(period="1d")

            if data.empty:
                print(f"[PriceService] No data found for {ticker}")
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