from backend.extraction.scoring.braden_calculator import calculate_braden_risk
def test_braden():
    assert calculate_braden_risk(8) == "VERY_HIGH_RISK"
    assert calculate_braden_risk(16) == "MILD_RISK"
    assert calculate_braden_risk(23) == "NO_RISK"
