from backend.extraction.gazetteers.cardiology import is_cardiology_term
def test_cardiology_terms():
    assert is_cardiology_term("AF") is True
    assert is_cardiology_term("STEMI") is True
    assert is_cardiology_term("Appendicitis") is False
