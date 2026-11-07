def calculate_news2_tier(total_score: int) -> str:
    if total_score >= 7:
        return "HIGH_RISK_EMERGENCY"
    elif total_score >= 5:
        return "MEDIUM_RISK_URGENT"
    elif total_score >= 1:
        return "LOW_RISK_WARD"
    return "NORMAL"
