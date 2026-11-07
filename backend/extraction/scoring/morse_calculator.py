def calculate_morse_fall_risk(score: int) -> str:
    if score >= 45:
        return "HIGH_RISK"
    elif score >= 25:
        return "MODERATE_RISK"
    return "LOW_NO_RISK"
