from backend.extraction.gazetteers.respiratory import is_respiratory_term
def test_respiratory_terms():
    assert is_respiratory_term("COPD") is True
    assert is_respiratory_term("Pneumonia") is True
    assert is_respiratory_term("Hypertension") is False
