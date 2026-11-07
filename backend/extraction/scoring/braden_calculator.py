def calculate_braden_risk(total_score: int) -> str:
    if total_score <= 9:
        return "VERY_HIGH_RISK"
    elif total_score <= 12:
        return "HIGH_RISK"
    elif total_score <= 14:
        return "MODERATE_RISK"
    elif total_score <= 18:
        return "MILD_RISK"
    return "NO_RISK"
