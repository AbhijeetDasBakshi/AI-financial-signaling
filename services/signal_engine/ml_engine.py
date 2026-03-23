"""
ML Signal Engine — trains a classifier on ticker's price history.
Runs per-ticker, cached for 1hr to avoid retraining every request.

Configure via .env:
    ML_MODEL=random_forest     (default)
    ML_HISTORY_PERIOD=6mo

Available models:
    random_forest    best for small datasets, default
    logistic         fast, interpretable
    svm              good for noisy data
    gradient_boost   most powerful, slower
"""
import time
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import os
from dotenv import load_dotenv

load_dotenv()

ML_MODEL     = os.getenv("ML_MODEL", "random_forest")
MODEL_TTL    = 3600   # retrain every 1hr

_model_cache: dict[str, tuple[float, dict]] = {}


def _get_model():
    models = {
        "random_forest":  RandomForestClassifier(n_estimators=100, random_state=42),
        "logistic":       LogisticRegression(max_iter=1000, random_state=42),
        "svm":            SVC(probability=True, random_state=42),
        "gradient_boost": GradientBoostingClassifier(n_estimators=100, random_state=42),
    }
    return models.get(ML_MODEL, models["random_forest"])


def _build_features(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)

    df["ma5"]        = df["price"].rolling(5).mean()
    df["ma10"]       = df["price"].rolling(10).mean()
    df["ma20"]       = df["price"].rolling(20).mean()
    df["pct_change"] = df["price"].pct_change()
    df["volatility"] = df["price"].rolling(5).std()
    df["vol_ma10"]   = df["volume"].rolling(10).mean()
    df["vol_ratio"]  = df["volume"] / df["vol_ma10"]

    delta     = df["price"].diff()
    gain      = delta.clip(lower=0).rolling(14).mean()
    loss      = (-delta.clip(upper=0)).rolling(14).mean()
    rs        = gain / loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))

    df["ma5_ma10_ratio"] = df["ma5"]  / df["ma10"]
    df["ma5_ma20_ratio"] = df["ma5"]  / df["ma20"]

    # Target: 1 = next day up, 0 = next day down
    df["target"] = (df["price"].shift(-1) > df["price"]).astype(int)

    return df


def train_and_predict(records: list[dict]) -> dict:
    """Train ML model on ticker history and predict next direction."""
    if not records:
        return {"ml_signal": "INSUFFICIENT_DATA", "ml_confidence": 0.5, "ml_accuracy": None}

    ticker = records[0]["ticker"]
    now    = time.time()

    # Return cached result if within TTL
    if ticker in _model_cache:
        cached_time, cached_result = _model_cache[ticker]
        if now - cached_time < MODEL_TTL:
            remaining = int(MODEL_TTL - (now - cached_time))
            print(f"[ML] Using cached model for {ticker} — refreshes in {remaining}s")
            return cached_result

    print(f"[ML] Training {ML_MODEL} for {ticker} on {len(records)} records...")

    feature_cols = [
        "ma5", "ma10", "ma20", "pct_change", "volatility",
        "vol_ratio", "rsi", "ma5_ma10_ratio", "ma5_ma20_ratio"
    ]

    df = _build_features(records).dropna(subset=feature_cols + ["target"])

    if len(df) < 20:
        print(f"[ML] Not enough clean data ({len(df)} rows)")
        return {"ml_signal": "INSUFFICIENT_DATA", "ml_confidence": 0.5, "ml_accuracy": None, "data_points": len(df)}

    X = df[feature_cols].values
    y = df["target"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    model = _get_model()
    model.fit(X_train, y_train)

    accuracy = round(accuracy_score(y_test, model.predict(X_test)), 4)
    print(f"[ML] Accuracy: {accuracy*100:.1f}% | Model: {ML_MODEL} | Data: {len(df)} rows")

    X_latest   = scaler.transform([X[-1]])
    prediction = model.predict(X_latest)[0]
    proba      = model.predict_proba(X_latest)[0]

    importance = {}
    if hasattr(model, "feature_importances_"):
        importance = dict(sorted(
            zip(feature_cols, [round(float(v), 4) for v in model.feature_importances_]),
            key=lambda x: x[1], reverse=True
        ))

    result = {
        "ml_signal":          "BUY" if prediction == 1 else "SELL",
        "ml_confidence":      round(float(max(proba)), 4),
        "ml_accuracy":        accuracy,
        "ml_model":           ML_MODEL,
        "data_points":        len(df),
        "feature_importance": importance,
    }

    _model_cache[ticker] = (now, result)
    return result
