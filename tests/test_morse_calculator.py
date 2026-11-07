from backend.extraction.scoring.morse_calculator import calculate_morse_fall_risk
def test_morse():
    assert calculate_morse_fall_risk(50) == "HIGH_RISK"
    assert calculate_morse_fall_risk(30) == "MODERATE_RISK"
    assert calculate_morse_fall_risk(10) == "LOW_NO_RISK"
