from backend.extraction.scoring.news2_calculator import calculate_news2_tier
def test_news2():
    assert calculate_news2_tier(8) == "HIGH_RISK_EMERGENCY"
    assert calculate_news2_tier(5) == "MEDIUM_RISK_URGENT"
    assert calculate_news2_tier(0) == "NORMAL"
