"""
Transform raw prices from PostgreSQL:
- % change from previous close
- Moving averages (MA5, MA10)
- Daily range (high - low)
- Min-max normalization
"""
import pandas as pd


def transform_prices(records: list[dict]) -> list[dict]:
    if not records:
        print("[Transform] No price records to transform")
        return []

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)

    df["pct_change"]  = df["price"].pct_change().round(6)
    df["ma5"]         = df["price"].rolling(window=5).mean().round(4)
    df["ma10"]        = df["price"].rolling(window=10).mean().round(4)
    df["daily_range"] = (df["high"] - df["low"]).round(4)

    min_p = df["price"].min()
    max_p = df["price"].max()
    df["price_normalized"] = (
        ((df["price"] - min_p) / (max_p - min_p)).round(6)
        if max_p != min_p else 0.0
    )

    df = df.where(pd.notna(df), other=None)

    result = df.to_dict(orient="records")
    print(f"[Transform] {len(result)} price records transformed")
    return result
