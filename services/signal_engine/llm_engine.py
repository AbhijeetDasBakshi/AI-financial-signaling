"""
LLM explanation engine — Groq + OpenRouter support.
Configure via .env:

    LLM_PROVIDER=groq                         (or openrouter)
    GROQ_API_KEY=your_key_here
    GROQ_MODEL=llama3-8b-8192

Free Groq models:
    llama3-8b-8192             fast, default
    llama3-70b-8192            most powerful
    mixtral-8x7b-32768         long context
    llama-3.1-70b-versatile    latest

Free OpenRouter models (set LLM_PROVIDER=openrouter):
    meta-llama/llama-3.1-8b-instruct:free
    meta-llama/llama-3.3-70b-instruct:free
    deepseek/deepseek-r1:free
    mistralai/mistral-7b-instruct:free
    qwen/qwen-2.5-72b-instruct:free
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER       = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
GROQ_MODEL         = os.getenv("GROQ_MODEL", "llama3-8b-8192")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
MAX_TOKENS         = int(os.getenv("LLM_MAX_TOKENS", "500"))
TEMPERATURE        = float(os.getenv("LLM_TEMPERATURE", "0.3"))


def build_prompt(ticker: str, signal_data: dict, news_headlines: list[str]) -> str:
    f         = signal_data.get("price_features") or {}
    reasons   = "\n".join(f"- {r}" for r in signal_data.get("reasons", []))
    headlines = "\n".join(f"- {h}" for h in news_headlines[:5]) if news_headlines else "- No recent news"

    # Rich historical context
    rsi_text  = f"{f.get('rsi'):.1f}" if f.get("rsi") else "N/A"
    vol_text  = f"{f.get('vol_vs_avg'):.1f}x avg" if f.get("vol_vs_avg") else "N/A"
    high_text = f"${f.get('high_52w'):.2f}" if f.get("high_52w") else "N/A"
    low_text  = f"${f.get('low_52w'):.2f}"  if f.get("low_52w")  else "N/A"
    pts_text  = f.get("data_points", "N/A")
    per_text  = f.get("period", "N/A")

    return f"""You are a financial analyst AI. Analyze this market data and give a clear investment explanation.

TICKER: {ticker}
SIGNAL: {signal_data.get('signal')} (confidence: {signal_data.get('confidence')})

PRICE DATA ({pts_text} days of history, period: {per_text}):
  Current price:  ${f.get('price', 'N/A')}
  MA5:            {f.get('ma5', 'N/A')}
  MA10:           {f.get('ma10', 'N/A')}
  MA20:           {f.get('ma20', 'N/A')}
  RSI (14):       {rsi_text}
  Price change:   {f.get('pct_change', 'N/A')}
  Volume:         {vol_text}
  52w high:       {high_text}
  52w low:        {low_text}

SENTIMENT SCORE: {signal_data.get('sentiment')} (-1 very negative → +1 very positive)

SIGNAL REASONS:
{reasons}

RECENT NEWS:
{headlines}

Write a 4-5 sentence analysis of the {signal_data.get('signal')} signal for {ticker}.
Reference specific numbers (price, RSI, MA values). 
Explain what the data means for an investor.
End with the single biggest risk to watch.
Write in plain professional language. No bullet points."""


def _call_groq(prompt: str) -> str:
    from groq import Groq
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env")
    client   = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a concise financial analyst. Give clear, data-driven investment insights."},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content.strip()


def _call_openrouter(prompt: str, retries: int = 3) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in .env")
    for attempt in range(retries):
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://github.com/financial-signaling",
                "X-Title":       "Financial Signaling",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a concise financial analyst."},
                    {"role": "user",   "content": prompt}
                ],
                "max_tokens":  MAX_TOKENS,
                "temperature": TEMPERATURE,
            },
            timeout=30
        )
        if response.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"[LLM] Rate limited. Retrying in {wait}s...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    raise Exception("Rate limit exceeded after retries")


def _rule_based_summary(signal_data: dict) -> str:
    signal    = signal_data.get("signal", "HOLD")
    sentiment = signal_data.get("sentiment", 0)
    reasons   = " ".join(signal_data.get("reasons", []))
    label     = "positive" if sentiment > 0.2 else "negative" if sentiment < -0.2 else "neutral"
    return (
        f"Signal: {signal}. News sentiment is {label} ({sentiment:.3f}). "
        f"{reasons}. LLM explanation temporarily unavailable."
    )


def get_llm_explanation(ticker: str, signal_data: dict, news_headlines: list[str] = None) -> str:
    """Get LLM explanation. Provider set via LLM_PROVIDER in .env."""
    try:
        prompt = build_prompt(ticker, signal_data, news_headlines or [])
        if LLM_PROVIDER == "groq":
            print(f"[LLM] Groq | {GROQ_MODEL}")
            return _call_groq(prompt)
        elif LLM_PROVIDER == "openrouter":
            print(f"[LLM] OpenRouter | {OPENROUTER_MODEL}")
            return _call_openrouter(prompt)
        else:
            return f"Unknown LLM_PROVIDER: {LLM_PROVIDER}"
    except Exception as e:
        print(f"[LLM ERROR]: {e}")
        return _rule_based_summary(signal_data)