from backend.extraction.gazetteers.neurology import is_neurology_term
def test_neurology_terms():
    assert is_neurology_term("Stroke") is True
    assert is_neurology_term("TIA") is True
    assert is_neurology_term("Gastritis") is False
