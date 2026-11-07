from backend.extraction.gazetteers.endocrinology import is_endocrinology_term
def test_endocrinology_terms():
    assert is_endocrinology_term("DKA") is True
    assert is_endocrinology_term("T2DM") is True
    assert is_endocrinology_term("Stroke") is False
