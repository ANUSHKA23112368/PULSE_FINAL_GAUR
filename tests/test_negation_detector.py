"""
Tests for Clinical Negation & Uncertainty Scoping.
"""

from backend.extraction.negation_detector import check_assertion

def test_negated_entity():
    sent = "Patient denies chest pain and has no fever."
    is_neg, is_unc = check_assertion(sent, "chest pain")
    assert is_neg is True
    assert is_unc is False

def test_uncertain_entity():
    sent = "Admitted with suspected pneumonia and query UTI."
    is_neg, is_unc = check_assertion(sent, "pneumonia")
    assert is_unc is True
    assert is_neg is False

def test_positive_entity():
    sent = "Patient has severe shortness of breath."
    is_neg, is_unc = check_assertion(sent, "shortness of breath")
    assert is_neg is False
    assert is_unc is False
