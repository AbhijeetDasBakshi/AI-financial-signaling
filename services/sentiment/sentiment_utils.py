def sentiment_label(score: float) -> str:
    if score > 0.2:
        return "POSITIVE"
    elif score < -0.2:
        return "NEGATIVE"
    return "NEUTRAL"