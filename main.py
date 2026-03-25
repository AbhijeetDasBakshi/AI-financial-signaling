from fastapi import FastAPI
from api.routes import price, news, ingest, analyze, etl, signal, portfolio, backtest

app = FastAPI(
    title="Financial Signaling API",
    description="Real-time stock analysis and buy/sell signal generation with backtesting",
    version="1.1.0"
)

# Register all routes
app.include_router(price.router)
app.include_router(news.router)
app.include_router(ingest.router)
app.include_router(analyze.router)
app.include_router(etl.router)
app.include_router(signal.router)
app.include_router(portfolio.router)
app.include_router(backtest.router)

@app.get("/")
def root():
    return {
        "status":    "running",
        "docs":      "/docs",
        "endpoints": {
            "analyze":   "POST /analyze/?ticker=NVDA",
            "backtest":  "GET  /backtest/?ticker=NVDA&period=6mo",
            "signal":    "GET  /signal/?ticker=NVDA",
            "price":     "GET  /price/?ticker=NVDA",
        }
    }