"""
Layer 5 Signal Engine Test
Run: python tests/test_signal.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.signal_engine.rule_engine import compute_signal
from services.signal_engine.llm_engine import get_llm_explanation
from database.db import news_collection

TICKER = "NVDA"

print(f"\n{'='*50}")
print(f"  LAYER 5 SIGNAL TEST — {TICKER}")
print(f"{'='*50}")

# Step 1 — rule engine
print("\n[1] Running rule engine...")
signal_data = compute_signal(TICKER)
print(f"    Signal:     {signal_data['signal']}")
print(f"    Confidence: {signal_data['confidence']}")
print(f"    Score:      {signal_data['score']}")
print(f"    Sentiment:  {signal_data['sentiment']}")
print(f"    Reasons:")
for r in signal_data["reasons"]:
    print(f"      - {r}")

# Step 2 — LLM explanation
print("\n[2] Getting LLM explanation from Groq...")
headlines = [
    doc.get("title", "") for doc in
    news_collection.find({"ticker": TICKER}, {"_id": 0, "title": 1})
    .sort("ingested_at", -1).limit(5)
    if doc.get("title")
]
explanation = get_llm_explanation(TICKER, signal_data, headlines)
print(f"\n    Explanation:\n    {explanation}")

print(f"\n{'='*50}")
print("  LAYER 5 TEST COMPLETE ✓")
print(f"{'='*50}\n")
