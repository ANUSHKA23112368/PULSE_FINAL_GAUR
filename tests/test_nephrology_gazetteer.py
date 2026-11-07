from backend.extraction.gazetteers.nephrology import is_nephrology_term
def test_nephrology_terms():
    assert is_nephrology_term("AKI") is True
    assert is_nephrology_term("CKD") is True
    assert is_nephrology_term("Asthma") is False
