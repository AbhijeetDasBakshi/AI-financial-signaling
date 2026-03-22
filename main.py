from fastapi import FastAPI
from api.routes import price, news, ingest, analyze, etl

app = FastAPI(
    title="Financial Signaling API",
    description="Real-time stock analysis and buy/sell signal generation",
    version="1.0.0"
)

# Register all routes
app.include_router(price.router)
app.include_router(news.router)
app.include_router(ingest.router)
app.include_router(analyze.router)
app.include_router(etl.router)


@app.get("/")
def root():
    return {"status": "running", "docs": "/docs"}
