"""
Confidence scoring engine.
Combines rule-based + ML signals to compute final confidence.
More signals agreeing = higher confidence.
"""


def compute_combined_signal(rule_result: dict, ml_result: dict) -> dict:
    """
    Combine rule-based and ML signals.

    Agreement levels:
    - Both agree on same signal → STRONG — high confidence
    - One says HOLD, other has signal → MODERATE — medium confidence
    - Both disagree (BUY vs SELL) → CONFLICTED — HOLD with low confidence
    """
    rule_signal = rule_result.get("signal", "HOLD")
    ml_signal   = ml_result.get("signal",   "HOLD")
    rule_conf   = rule_result.get("confidence", 0.5)
    ml_conf     = ml_result.get("confidence",   0.5)
    ml_accuracy = ml_result.get("accuracy", 0.5) or 0.5

    # Weight ML by its accuracy
    ml_weight   = float(ml_accuracy)
    rule_weight = 1.0

    signals    = [rule_signal, ml_signal]
    hold_count = signals.count("HOLD")

    # Both agree
    if rule_signal == ml_signal:
        final_signal = rule_signal
        avg_conf     = (rule_conf * rule_weight + ml_conf * ml_weight) / (rule_weight + ml_weight)
        final_conf   = min(avg_conf + 0.1, 0.95)
        agreement    = "STRONG"

    # One is HOLD
    elif hold_count == 1:
        final_signal = rule_signal if rule_signal != "HOLD" else ml_signal
        final_conf   = round((rule_conf + ml_conf) / 2, 2)
        agreement    = "MODERATE"

    # BUY vs SELL conflict
    else:
        final_signal = "HOLD"
        final_conf   = 0.5
        agreement    = "CONFLICTED"

    return {
        "signal":      final_signal,
        "confidence":  round(final_conf, 2),
        "agreement":   agreement,
        "rule_signal": rule_signal,
        "ml_signal":   ml_signal,
        "rule_conf":   rule_conf,
        "ml_conf":     ml_conf,
        "ml_accuracy": ml_accuracy,
    }
