from backend.extraction.scoring.gcs_calculator import calculate_gcs
def test_gcs():
    res = calculate_gcs(4, 5, 6)
    assert res["total_score"] == 15
    assert res["severity"] == "Mild"
    res_low = calculate_gcs(1, 2, 3)
    assert res_low["total_score"] == 6
    assert res_low["severity"] == "Severe"
