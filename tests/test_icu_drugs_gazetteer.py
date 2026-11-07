from backend.extraction.gazetteers.icu_drugs import is_icu_drug
def test_icu_drugs():
    assert is_icu_drug("Noradrenaline") is True
    assert is_icu_drug("Propofol") is True
    assert is_icu_drug("Paracetamol") is False
