def assess_risk(amount: float, source_currency: str, target_currency: str) -> str:

    # Very simple rule-based risk scoring
    a = float(amount)

    if a >= 10000:
        return "HIGH"
    
    if a >= 1000:
        return "MEDIUM"
    
    return "LOW"
